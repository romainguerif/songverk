/* Fonction Cloudflare Pages : stockage des songs dans un namespace KV.
   Nécessite un binding KV nommé SONGVERK.
   L'authentification est assurée par Cloudflare Access devant le site :
   sans elle, cette API est ouverte à qui connaît l'URL. */

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });

export async function onRequest({ request, env, params }) {
  const kv = env.SONGVERK;
  if (!kv) return json({ error: "binding KV SONGVERK absent" }, 500);

  const parts = params.route || [];
  const method = request.method;

  // GET /api/index -> liste légère pour la fusion
  if (parts[0] === "index" && method === "GET") {
    const idx = await kv.get("index", "json");
    return json({ songs: idx || [] });
  }

  if (parts[0] === "song" && parts[1]) {
    const id = parts[1];

    if (method === "GET") {
      const s = await kv.get("song:" + id, "json");
      return s ? json(s) : json({ error: "introuvable" }, 404);
    }

    if (method === "PUT") {
      let song;
      try { song = await request.json(); } catch { return json({ error: "json invalide" }, 400); }
      if (!song || song.id !== id) return json({ error: "id incohérent" }, 400);
      song.updatedAt = song.updatedAt || Date.now();

      await kv.put("song:" + id, JSON.stringify(song));
      const idx = (await kv.get("index", "json")) || [];
      const entry = { id, name: song.name, updatedAt: song.updatedAt, rows: (song.rows || []).length };
      const i = idx.findIndex(e => e.id === id);
      if (i < 0) idx.push(entry); else idx[i] = entry;
      await kv.put("index", JSON.stringify(idx));
      return json({ ok: true, updatedAt: song.updatedAt });
    }

    if (method === "DELETE") {
      await kv.delete("song:" + id);
      const idx = ((await kv.get("index", "json")) || []).filter(e => e.id !== id);
      await kv.put("index", JSON.stringify(idx));
      return json({ ok: true });
    }
  }

  return json({ error: "route inconnue" }, 404);
}
