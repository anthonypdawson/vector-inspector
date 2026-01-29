## Netlify Function: Append Telemetry to a File in GitHub

This function:

- Accepts a POST with your telemetry payload
- Validates a shared secret header
- Fetches a file from GitHub
- Appends a new NDJSON line
- Writes the updated file back to GitHub

### `netlify/functions/telemetry.js`

```js
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
```

---

## Required Environment Variables

```
TELEMETRY_SECRET=your-shared-secret
GITHUB_TOKEN=your-github-token
GITHUB_REPO_OWNER=your-username-or-org
GITHUB_REPO_NAME=your-repo
GITHUB_FILE_PATH=data/models.ndjson
```

---

## Expected Payload (from your app)

```json
{
"modelName": "my-private-model",
"dimension": 1536,
"provider": "custom",
"loadedSuccessfully": true
}
```

Sent with header:

```
X-Telemetry-Key: <your-secret>
```

---

## Why this works well

- Append‑only NDJSON avoids merge conflicts
- GitHub handles versioning automatically
- Your local script can easily parse the file
- No database, no servers, no complexity
- Fully aligned with your minimal, intentional architecture