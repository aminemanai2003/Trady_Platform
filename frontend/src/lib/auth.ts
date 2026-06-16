import { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import GoogleProvider from "next-auth/providers/google";
import GitHubProvider from "next-auth/providers/github";
import { compare, hash } from "bcryptjs";
import prisma from "@/lib/prisma";
import { ensureUserSubscription } from "@/lib/billing";

type UserProfileRow = {
    id: string;
    image: string | null;
};

async function getUserProfileByEmail(email: string) {
    const rows = await prisma.$queryRaw<UserProfileRow[]>`
        SELECT id, image FROM "user" WHERE email = ${email} LIMIT 1
    `;
    return rows[0] ?? null;
}

const configuredOAuthProviders = [
    process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET
        ? GoogleProvider({
            clientId: process.env.GOOGLE_CLIENT_ID,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET,
        })
        : null,
    process.env.GITHUB_ID && process.env.GITHUB_SECRET
        ? GitHubProvider({
            clientId: process.env.GITHUB_ID,
            clientSecret: process.env.GITHUB_SECRET,
        })
        : null,
];

const oauthProviders = configuredOAuthProviders.filter(
    (provider): provider is NonNullable<(typeof configuredOAuthProviders)[number]> => provider !== null
);

export const authOptions: NextAuthOptions = {
    providers: [
        CredentialsProvider({
            name: "credentials",
            credentials: {
                email: { label: "Email", type: "email" },
                password: { label: "Password", type: "password" },
            },
            async authorize(credentials) {
                try {
                    if (!credentials?.email || !credentials?.password) {
                        throw new Error("Email and password required");
                    }

                    const user = await prisma.user.findUnique({
                        where: { email: credentials.email },
                    });

                    if (!user) throw new Error("No account found with this email");

                    const isValid = await compare(credentials.password, user.hashedPassword);
                    if (!isValid) throw new Error("Invalid password");

                    const profile = await getUserProfileByEmail(user.email);
                    return { id: user.id, name: user.name, email: user.email, image: profile?.image ?? null };
                } catch (error) {
                    console.error("Auth error:", error);
                    return null;
                }
            },
        }),
        ...oauthProviders,
    ],
    session: { strategy: "jwt" },
    pages: {
        signIn: "/login",
    },
    callbacks: {
        async signIn({ account, user }) {
            if (account?.provider === "credentials") return true;
            if (!user.email) return false;

            const placeholderPassword = await hash(
                `oauth:${account?.provider ?? "provider"}:${account?.providerAccountId ?? user.email}:${process.env.NEXTAUTH_SECRET ?? "trady"}`,
                10
            );

            const dbUser = await prisma.user.upsert({
                where: { email: user.email },
                update: { name: user.name },
                create: {
                    email: user.email,
                    name: user.name,
                    hashedPassword: placeholderPassword,
                },
            });
            await ensureUserSubscription(dbUser.id);
            if (user.image) {
                await prisma.$executeRaw`
                    UPDATE "user"
                    SET image = ${user.image}
                    WHERE id = ${dbUser.id} AND (image IS NULL OR image = '')
                `;
            }

            return true;
        },
        async jwt({ token, user }) {
            if (user) {
                token.id = user.id;
                if (user.image) token.picture = user.image;
            }
            if (token.email) {
                const dbUser = await getUserProfileByEmail(token.email);
                if (dbUser) {
                    token.id = dbUser.id;
                    token.picture = dbUser.image ?? token.picture;
                }
            }
            return token;
        },
        async session({ session, token }) {
            if (session.user) {
                (session.user as { id?: string; image?: string | null }).id = token.id as string;
                (session.user as { id?: string; image?: string | null }).image = (token.picture as string | undefined) ?? null;
            }
            return session;
        },
    },
    secret: process.env.NEXTAUTH_SECRET,
};
