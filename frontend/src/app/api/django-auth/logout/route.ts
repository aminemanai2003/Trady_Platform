import { NextResponse } from "next/server";
import { DJANGO_TOKEN_COOKIE } from "@/lib/django-auth";

export async function POST() {
    const response = NextResponse.json({ success: true });
    response.cookies.delete(DJANGO_TOKEN_COOKIE);
    response.cookies.delete("sessionid");
    return response;
}