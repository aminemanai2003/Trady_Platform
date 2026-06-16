import { NextRequest, NextResponse } from "next/server";

export const DJANGO_TOKEN_COOKIE = "django_token";

export function appendUpstreamSetCookie(response: NextResponse, setCookie: string | null) {
    if (setCookie) {
        response.headers.append("set-cookie", setCookie);
    }
}

export function getDjangoAuthHeader(req: NextRequest): string {
    const explicitHeader = req.headers.get("authorization");
    if (explicitHeader) {
        return explicitHeader;
    }

    const token = req.cookies.get(DJANGO_TOKEN_COOKIE)?.value;
    return token ? `Token ${token}` : "";
}

export function getForwardedCookieHeader(req: NextRequest): string {
    return req.headers.get("cookie") ?? "";
}

export function setDjangoTokenCookie(response: NextResponse, token: unknown) {
    if (typeof token !== "string" || !token.trim()) {
        return;
    }

    response.cookies.set({
        name: DJANGO_TOKEN_COOKIE,
        value: token,
        httpOnly: true,
        sameSite: "lax",
        secure: process.env.NODE_ENV === "production",
        path: "/",
        maxAge: 60 * 60 * 24 * 30,
    });
}