const { authorizeRefresh, queueRefresh } = require("./refresh-core.cjs");

module.exports = async function handler(request, response) {
  if (request.method !== "POST") {
    response.setHeader("Allow", "POST");
    return response.status(405).json({ ok: false, error: "Method not allowed" });
  }

  const authorization = authorizeRefresh(request, process.env.REFRESH_SECRET);
  if (!authorization.ok) {
    return response.status(authorization.status).json({ ok: false, error: authorization.error });
  }

  const result = await queueRefresh();
  return response.status(result.status).json(result.payload);
};
