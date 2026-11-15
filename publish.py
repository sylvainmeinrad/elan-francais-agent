"""Agent de publication Instagram — Élan Français.

Lancé toutes les 10 minutes par GitHub Actions. Publie chaque élément de
schedule.json dont l'heure est passée et qui n'est pas encore dans
published.json, via l'API Instagram (Instagram Login).

Variables d'environnement :
  IG_TOKEN    jeton d'accès Instagram (secret GitHub)
  IG_USER_ID  identifiant du compte Instagram (secret GitHub)
  MEDIA_BASE  URL publique du dossier docs/ (GitHub Pages), sans / final
  MODE        "publish" (défaut) ou "check" (vérifie le jeton et les fichiers, ne publie rien)
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

TOKEN = os.environ.get("IG_TOKEN", "").strip()
if not TOKEN:
    print("Secret IG_TOKEN absent : rien à faire tant qu'il n'est pas ajouté.")
    sys.exit(0)
# Jeton « Instagram login » (IGAA…) → graph.instagram.com ; jeton Facebook / utilisateur système → graph.facebook.com
API = ("https://graph.instagram.com/v21.0" if TOKEN.startswith("IG")
       else "https://graph.facebook.com/v21.0")
USER = os.environ.get("IG_USER_ID", "").strip() or "me"
BASE = os.environ["MEDIA_BASE"].rstrip("/")
MODE = os.environ.get("MODE", "publish")
MAX_LATE = timedelta(hours=6)      # au-delà, on ne publie plus et on le signale
MAX_PER_RUN = 4                    # garde le passage court ; le reste part au suivant


def call(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} → HTTP {e.code}: {body}") from None


def url_ok(u):
    req = urllib.request.Request(u, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status == 200
    except Exception:
        return False


def wait_ready(cid, video):
    """Attend que le conteneur soit prêt (les vidéos sont traitées par Instagram)."""
    for _ in range(60 if video else 20):
        st = call("GET", cid, fields="status_code,status")
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"conteneur {cid} : {st}")
        time.sleep(10 if video else 3)
    raise RuntimeError(f"conteneur {cid} pas prêt à temps")


def publish(item):
    urls = [f"{BASE}/{f}" for f in item["files"]]
    k = item["kind"]
    if k == "REEL":
        c = call("POST", f"{USER}/media", media_type="REELS", video_url=urls[0],
                 caption=item["caption"], share_to_feed="true", thumb_offset="1500")
        wait_ready(c["id"], True)
    elif k == "STORY":
        c = call("POST", f"{USER}/media", media_type="STORIES", image_url=urls[0])
        wait_ready(c["id"], False)
    elif k == "CAROUSEL":
        kids = []
        for u in urls[:10]:
            ch = call("POST", f"{USER}/media", image_url=u, is_carousel_item="true")
            wait_ready(ch["id"], False)
            kids.append(ch["id"])
        c = call("POST", f"{USER}/media", media_type="CAROUSEL",
                 children=",".join(kids), caption=item["caption"])
        wait_ready(c["id"], False)
    else:
        raise ValueError(k)
    return call("POST", f"{USER}/media_publish", creation_id=c["id"])["id"]


def main():
    sched = json.load(open("schedule.json", encoding="utf-8"))
    pub = json.load(open("published.json", encoding="utf-8"))
    done = {p["id"] for p in pub}

    if MODE == "check":
        me = call("GET", USER, fields="id,username,account_type")
        print("Compte :", me)
        lim = call("GET", f"{USER}/content_publishing_limit", fields="quota_usage,config")
        print("Quota de publication :", lim)
        nxt = [i for i in sched if i["id"] not in done][:3]
        for i in nxt:
            for f in i["files"][:2]:
                u = f"{BASE}/{f}"
                print("OK " if url_ok(u) else "INTROUVABLE ", u)
        return

    now = datetime.now(timezone.utc)
    due = [i for i in sched if i["id"] not in done and datetime.fromisoformat(i["when"]) <= now]
    errors = []
    for item in due[:MAX_PER_RUN]:
        late = now - datetime.fromisoformat(item["when"])
        if late > MAX_LATE:
            pub.append({"id": item["id"], "status": "skipped_too_late", "at": now.isoformat()})
            errors.append(f"{item['id']} : trop en retard ({late}), non publié")
            continue
        try:
            mid = publish(item)
            pub.append({"id": item["id"], "status": "published", "media_id": mid, "at": now.isoformat()})
            print("Publié :", item["id"], mid)
        except Exception as e:
            errors.append(f"{item['id']} : {e}")
            print("ÉCHEC :", item["id"], e)
        json.dump(pub, open("published.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not due:
        print("Rien à publier pour l'instant.")
    if errors:
        print("\n".join(errors))
        sys.exit(1)        # GitHub envoie un e-mail en cas d'échec


if __name__ == "__main__":
    main()
