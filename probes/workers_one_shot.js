export default {
  async fetch(request) {
    if (request.method !== "POST") return new Response("One-shot probe ready. POST /probe to test the verified Alpha123 API.");
    const url = "https://alpha123.uk/api/data?fresh=0";
    const result = { tested_at: new Date().toISOString(), source: "Cloudflare Workers Playground edge sandbox", url };
    try {
      const response = await fetch(url, { redirect: "manual", signal: AbortSignal.timeout(20000) });
      result.status = response.status;
      result.content_type = response.headers.get("content-type");
      result.cf_mitigated = response.headers.get("cf-mitigated");
      if (response.status === 403 || result.cf_mitigated === "challenge") {
        result.outcome = "STOP_ACCESS_DENIED";
        result.parsed = false;
        return Response.json(result);
      }
      if (response.status !== 200 || !(result.content_type || "").includes("application/json")) {
        result.outcome = "NOT_VALID_JSON_RESPONSE";
        result.parsed = false;
        return Response.json(result);
      }
      const data = await response.json();
      if (!data || !Array.isArray(data.airdrops)) throw new Error("INVALID_AIRDROPS_SCHEMA");
      const today = new Date(Date.now() + 8 * 3600000).toISOString().slice(0,10);
      result.beijing_date = today;
      result.total_airdrops = data.airdrops.length;
      result.today = data.airdrops.filter(a => a.date === today).map(a => ({id:a.id,token:a.token,name:a.name,points:a.points,amount:a.amount,time:a.beijing_time || a.time || "待公布",date:a.date,phase:a.phase}));
      result.dated_rows = data.airdrops.filter(a=>typeof a.date === "string").length;
      result.outcome = "JSON_PARSED_DATE_FILTER";
      result.parsed = true;
      return Response.json(result);
    } catch (error) {
      result.outcome = "PROBE_ERROR";
      result.error_type = error.name;
      result.parsed = false;
      return Response.json(result);
    }
  }
};