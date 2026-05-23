import fetch from "node-fetch";

export async function handler(event, context) {
    // Only allow POST
    if (event.httpMethod !== "POST") {
        return { statusCode: 405, body: "Method Not Allowed" };
    }

    // Validate shared secret
    const secret = process.env.TELEMETRY_SECRET;
    const provided = event.headers["x-telemetry-key"];
    if (!secret || provided !== secret) {
        return { statusCode: 401, body: "Unauthorized" };
    }

    // Parse payload
    let payload;
    try {
        payload = JSON.parse(event.body);
    } catch {
        return { statusCode: 400, body: "Invalid JSON" };
    }

    // GitHub repo info
    const owner = process.env.GITHUB_REPO_OWNER;
    const repo = process.env.GITHUB_REPO_NAME;
    const path = process.env.GITHUB_FILE_PATH;
    const token = process.env.GITHUB_TOKEN;

    const githubHeaders = {
        "Authorization": `Bearer ${token}`,
        "Accept": "application/vnd.github+json"
    };

    // 1. Fetch existing file
    const getRes = await fetch(
        `https://api.github.com/repos/${owner}/${repo}/contents/${path}`,
        { headers: githubHeaders }
    );

    if (!getRes.ok) {
        return { statusCode: 500, body: "Failed to fetch file from GitHub" };
    }

    const fileData = await getRes.json();
    const sha = fileData.sha;
    const existingContent = Buffer.from(fileData.content, "base64").toString("utf8");

    // 2. Append new NDJSON line
    const newLine = JSON.stringify(payload);
    const updatedContent = existingContent + "\n" + newLine;

    // 3. Write updated file back to GitHub
    const putRes = await fetch(
        `https://api.github.com/repos/${owner}/${repo}/contents/${path}`,
        {
            method: "PUT",
            headers: githubHeaders,
            body: JSON.stringify({
                message: "Append telemetry entry",
                content: Buffer.from(updatedContent).toString("base64"),
                sha
            })
        }
    );

    if (!putRes.ok) {
        return { statusCode: 500, body: "Failed to update file in GitHub" };
    }

    return { statusCode: 200, body: "OK" };
}