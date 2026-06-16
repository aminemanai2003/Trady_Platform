import { withAuth } from "next-auth/middleware";

export default withAuth({
    pages: { signIn: "/login" },
});

export const config = {
    matcher: [
        "/dashboard/:path*",
        "/agents/:path*",
        "/billing/:path*",
        "/billing",
        "/news/:path*",
        "/news",
        "/reports/:path*",
        "/trading/:path*",
        "/strategy-tutor/:path*",
        "/strategy-tutor",
        "/backtesting/:path*",
        "/backtesting",
    ],
};

