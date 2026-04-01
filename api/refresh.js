module.exports = async function handler(request, response) {
  if (request.method !== "POST") {
    response.setHeader("Allow", "POST");
    return response.status(405).json({ ok: false, error: "Method not allowed" });
  }

  const token = process.env.GITHUB_TOKEN;
  const repository = process.env.GITHUB_REPOSITORY || "neelimasap/dress-deals";
  const workflowId = process.env.GITHUB_REFRESH_WORKFLOW || "daily-refresh.yml";
  const ref = process.env.GITHUB_REFRESH_REF || "main";

  if (!token) {
    return response.status(500).json({
      ok: false,
      error: "Missing GITHUB_TOKEN"
    });
  }

  const [owner, repo] = repository.split("/");
  if (!owner || !repo) {
    return response.status(500).json({
      ok: false,
      error: "Invalid GITHUB_REPOSITORY"
    });
  }

  try {
    const githubResponse = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflowId}/dispatches`,
      {
        method: "POST",
        headers: {
          Accept: "application/vnd.github+json",
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "User-Agent": "dress-deals-refresh"
        },
        body: JSON.stringify({
          ref,
          inputs: {
            source: "vercel-refresh"
          }
        })
      }
    );

    if (!githubResponse.ok) {
      const details = await githubResponse.text();
      return response.status(githubResponse.status).json({
        ok: false,
        error: "GitHub workflow dispatch failed",
        details
      });
    }

    return response.status(202).json({
      ok: true,
      message: "Refresh queued. GitHub Actions will update the data shortly."
    });
  } catch (error) {
    return response.status(500).json({
      ok: false,
      error: "Refresh request failed",
      details: error instanceof Error ? error.message : String(error)
    });
  }
};
