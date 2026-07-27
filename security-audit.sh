#!/usr/bin/env bash
# =============================================================================
#  security-audit.sh — neinvazivni black-box bezpecnostni sken vlastniho webu
# -----------------------------------------------------------------------------
#  CO DELA:  Posila jen ctouci pozadavky (GET/HEAD) na web, ktery ZADAS.
#            Kontroluje bezpecnostni hlavicky, TLS, unikle klice v JS,
#            zapomenute soubory (.git/.env/zalohy), admin cesty, WordPress.
#  CO NEDELA: nic nemaze, nic nemeni, NEspousti stazeny kod, nedela DoS,
#            neposila zadne utocne payloady do formularu, nebrute-forcuje.
#            Vsechno bezi jen proti jednomu webu, ktery mu zadas.
#
#  POUZITI:  bash security-audit.sh https://fymeko.cz
#            (bez argumentu pouzije https://fymeko.cz)
#            Vysledek se zaroven ulozi do souboru fymeko-audit-<datum>.txt
#
#  SPOUSTEJ JEN NA WEBU, KTERY VLASTNIS. Je to tvuj web = mas na to pravo.
# =============================================================================

set -u

# ---- parametry --------------------------------------------------------------
YES=0
if [ "${1:-}" = "-y" ]; then YES=1; shift; fi
TARGET="${1:-https://fymeko.cz}"
TARGET="${TARGET%/}"                                  # utni koncove lomitko
case "$TARGET" in http://*|https://*) ;; *) TARGET="https://$TARGET";; esac
HOST="$(printf '%s' "$TARGET" | sed -E 's#^https?://##; s#/.*$##')"

UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SLEEP=0.3                                             # slusny odstup mezi dotazy
CURL=(curl -sS --connect-timeout 10 --max-time 25 -A "$UA")
LOG="$(printf 'audit-%s-%s.txt' "$HOST" "$(date +%Y%m%d-%H%M%S)")"

# vsechno posli na obrazovku i do logu
exec > >(tee "$LOG") 2>&1

FAIL=0; WARN=0
pass(){ echo "  [ OK ]  $*"; }
warn(){ echo "  [WARN]  $*"; WARN=$((WARN+1)); }
fail(){ echo "  [FAIL]  $*"; FAIL=$((FAIL+1)); }
info(){ echo "  [info]  $*"; }
sect(){ echo; echo "=================================================================="; \
        echo "== $*"; echo "=================================================================="; }

if ! command -v curl >/dev/null 2>&1; then
  echo "Chybi 'curl'. Nainstaluj curl a spust znovu (Mac/Linux ho maji; Windows: pouzij Git Bash / WSL)."; exit 1
fi

echo "############################################################"
echo "#  Neinvazivni bezpecnostni sken"
echo "#  Cil:   $TARGET   (host: $HOST)"
echo "#  Cas:   $(date)"
echo "#  Log:   $LOG"
echo "############################################################"
if [ "$YES" != "1" ]; then
  printf "Spustit ctouci sken proti VYSE uvedenemu cili? [y/N] "
  read -r ans; case "$ans" in y|Y|yes|ano) ;; *) echo "Zruseno."; exit 0;; esac
fi

# ---- pomocnici na hlavicky ---------------------------------------------------
HDRS_ALL="$("${CURL[@]}" -sD - -o /dev/null -L "$TARGET/" | tr -d '\r')"
FINAL_HDRS="$(printf '%s\n' "$HDRS_ALL" | awk 'BEGIN{RS=""} {b=$0} END{print b}')"
has_hdr(){ printf '%s\n' "$FINAL_HDRS" | grep -qi "^$1:"; }
hdr(){ printf '%s\n' "$FINAL_HDRS" | grep -i "^$1:" | head -1 | cut -d: -f2- | sed 's/^[[:space:]]*//'; }

# =============================================================================
sect "1) Dostupnost, presmerovani a HTTP -> HTTPS"
if [ -z "$HDRS_ALL" ]; then
  fail "Web neodpovedel (zadne hlavicky). Zkontroluj domenu / pripojeni."; echo; echo "Konec."; exit 1
fi
echo "  Retezec presmerovani:"
printf '%s\n' "$HDRS_ALL" | grep -iE '^HTTP/|^location:' | sed 's/^/     /'
HTTP_HDR="$("${CURL[@]}" -sI "http://$HOST/" | tr -d '\r')"
if printf '%s' "$HTTP_HDR" | grep -qiE '^location:[[:space:]]*https://'; then
  pass "HTTP verze se presmerovava na HTTPS"
else
  warn "HTTP (port 80) se nepresmerovava na HTTPS — navstevnik muze zustat na nesifrovanem spojeni"
fi

# =============================================================================
sect "2) Bezpecnostni hlavicky"
if has_hdr "strict-transport-security"; then pass "HSTS: $(hdr strict-transport-security)"
else fail "Chybi HSTS (Strict-Transport-Security) — prohlizec nevynuti HTTPS"; fi

if has_hdr "content-security-policy"; then
  CSP="$(hdr content-security-policy)"
  pass "CSP je nastavene"
  echo "$CSP" | grep -qi "unsafe-inline" && warn "CSP obsahuje 'unsafe-inline' — velka cast ochrany proti XSS je pryc"
  echo "$CSP" | grep -qi "unsafe-eval"   && warn "CSP obsahuje 'unsafe-eval'"
else
  fail "Chybi Content-Security-Policy — hlavni obrana proti XSS neni zapnuta"
fi

if has_hdr "x-frame-options" || printf '%s' "${CSP:-}" | grep -qi "frame-ancestors"; then
  pass "Ochrana proti clickjackingu (X-Frame-Options / frame-ancestors) je nastavena"
else
  fail "Chybi X-Frame-Options i CSP frame-ancestors — web lze vlozit do ciziho <iframe> (clickjacking)"
fi

if printf '%s' "$(hdr x-content-type-options)" | grep -qi nosniff; then pass "X-Content-Type-Options: nosniff"
else warn "Chybi X-Content-Type-Options: nosniff"; fi

has_hdr "referrer-policy"   && pass "Referrer-Policy: $(hdr referrer-policy)"   || warn "Chybi Referrer-Policy"
has_hdr "permissions-policy" && pass "Permissions-Policy je nastavene"          || info "Chybi Permissions-Policy (nizka priorita)"

if printf '%s' "$(hdr access-control-allow-origin)" | grep -q '\*'; then
  warn "Access-Control-Allow-Origin: * — CORS otevreny vsem originum (prover, zda je zamer)"
fi

# =============================================================================
sect "3) Cookies"
COOKIES="$(printf '%s\n' "$FINAL_HDRS" | grep -i '^set-cookie:')"
if [ -z "$COOKIES" ]; then info "Titulni stranka nenastavuje zadne cookie"
else
  printf '%s\n' "$COOKIES" | while IFS= read -r c; do
    name="$(printf '%s' "$c" | sed -E 's/^set-cookie:[[:space:]]*//I; s/=.*$//')"
    echo "$c" | grep -qi 'secure'   || warn "Cookie '$name' bez priznaku Secure"
    echo "$c" | grep -qi 'httponly' || warn "Cookie '$name' bez priznaku HttpOnly (ctitelne z JS)"
    echo "$c" | grep -qi 'samesite' || warn "Cookie '$name' bez SameSite (riziko CSRF)"
  done
fi

# =============================================================================
sect "4) TLS certifikat (pokud je openssl)"
if command -v openssl >/dev/null 2>&1; then
  CERT="$(printf 'Q\n' | openssl s_client -connect "$HOST:443" -servername "$HOST" 2>/dev/null \
          | openssl x509 -noout -subject -issuer -dates 2>/dev/null)"
  if [ -n "$CERT" ]; then printf '%s\n' "$CERT" | sed 's/^/     /'; pass "Certifikat nacten"
  else warn "Nepodarilo se nacist certifikat pres openssl"; fi
else
  info "openssl neni k dispozici — pro hloubkovy test TLS pouzij ssllabs.com/ssltest"
fi

# =============================================================================
sect "5) Otisk serveru / technologie"
has_hdr "server"        && info "Server: $(hdr server)"
has_hdr "x-powered-by"  && warn "X-Powered-By: $(hdr x-powered-by) — zbytecne prozrazuje technologii/verzi"
HOME_HTML="$("${CURL[@]}" -L "$TARGET/")"
GEN="$(printf '%s' "$HOME_HTML" | grep -oiE '<meta[^>]+name="generator"[^>]*>' | head -1)"
[ -n "$GEN" ] && info "Generator meta: $GEN"
IS_WP=0
printf '%s' "$HOME_HTML" | grep -qiE 'wp-content|wp-includes|/wp-json' && IS_WP=1
[ "$IS_WP" = 1 ] && info "Detekovan WordPress (viz sekce 10)"

# =============================================================================
sect "6) Unikle klice / tajemstvi v klientskem kodu"
BLOB="$HOME_HTML"
JS_LIST="$(printf '%s' "$HOME_HTML" | grep -oiE 'src="[^"]+\.js[^"]*"' | sed -E 's/^src="//I; s/"$//')"
COUNT=0
while IFS= read -r js; do
  [ -z "$js" ] && continue
  [ "$COUNT" -ge 15 ] && break
  case "$js" in
    http://"$HOST"/*|https://"$HOST"/*) url="$js" ;;
    //"$HOST"/*)  url="https:$js" ;;
    http://*|https://*|//*) continue ;;            # cizi CDN preskoc
    /*)  url="$TARGET$js" ;;
    *)   url="$TARGET/$js" ;;
  esac
  BLOB="$BLOB
$("${CURL[@]}" "$url" 2>/dev/null)"
  COUNT=$((COUNT+1)); sleep "$SLEEP"
done <<EOF
$JS_LIST
EOF
info "Prohledano souboru JS (vlastni domena): $COUNT"
PATS='api[_-]?key|secret|client[_-]?secret|password[\"'"'"' ]*[:=]|bearer[[:space:]]|sk_(live|test)_|AIza[0-9A-Za-z_-]{20}|SG\.[A-Za-z0-9_-]{16}|AKIA[0-9A-Z]{16}|ghp_[0-9A-Za-z]{20}|supabase|firebaseio|firebaseapp|firebaseConfig|emailjs|formspree|mailgun|service_id|user_id[\"'"'"' ]*[:=]'
HITS="$(printf '%s' "$BLOB" | grep -oiE "$PATS" | tr 'A-Z' 'a-z' | sort | uniq -c | sort -rn)"
if [ -n "$HITS" ]; then
  warn "Nalezeny vzorky, ktere MOHOU byt citlive (over rucne, nektere jsou verejne 'anon' klice):"
  printf '%s\n' "$HITS" | sed 's/^/       /'
  echo "       >> Pokud je mezi tim skutecny tajny klic (sk_live_, SG., AKIA, heslo, service_role),"
  echo "          PRED odeslanim vystupu ho zacernI a klic ihned zneplatni/rotuj."
else
  pass "Zadne zjevne klice/tajemstvi v prohledanem klientskem kodu"
fi
# smiseny obsah (http zdroje na https strance)
if printf '%s' "$HOME_HTML" | grep -qiE '(src|href)="http://'; then
  warn "Smiseny obsah: na HTTPS strance se nacitaji zdroje pres http:// (viz src=/href=http://...)"
fi

# =============================================================================
sect "7) Formulare — kam tecou data"
FORMS="$(printf '%s' "$HOME_HTML" | grep -oiE '<form[^>]*>')"
if [ -n "$FORMS" ]; then printf '%s\n' "$FORMS" | sed 's/^/     /'
else info "Na titulni strance nenalezen zadny <form> (muze byt na /kontakt apod.)"; fi
SINKS="$(printf '%s' "$BLOB" | grep -oiE '(fetch\(|axios|emailjs\.send|formspree\.io/[a-z0-9]+|action=)"?[^" )<>]{0,80}' | sort -u)"
[ -n "$SINKS" ] && { echo "  Kam se posilaji data (endpointy/volani):"; printf '%s\n' "$SINKS" | sed 's/^/     /'; }

# =============================================================================
# baseline pro rozliseni "neexistuje" vs "existuje"
BOGUS="$("${CURL[@]}" -o /dev/null -w '%{http_code} %{size_download}' "$TARGET/zzz-neexistuje-$RANDOM$RANDOM" 2>/dev/null)"
BCODE="${BOGUS%% *}"; BLEN="${BOGUS##* }"
check_path(){                                    # $1=cesta $2=popis
  local out code len diff
  out="$("${CURL[@]}" -o /dev/null -w '%{http_code} %{size_download}' "$TARGET/$1" 2>/dev/null)"
  code="${out%% *}"; len="${out##* }"; sleep "$SLEEP"
  case "$code" in
    200) diff=$(( len>BLEN ? len-BLEN : BLEN-len ))
         if [ "$BCODE" = 200 ] && [ "$diff" -lt 64 ]; then :   # vypada jako soft-404
         else fail "$2 — HTTP 200 (${len}B): $TARGET/$1  <-- dostupne, prover"; fi ;;
    401|403) info "$2 — HTTP $code (existuje, ale chranene): /$1" ;;
    500|503) warn "$2 — HTTP $code (serverova chyba): /$1" ;;
  esac
}
check_content(){                                 # $1=cesta $2=popis $3=signatura(regex)
  local body code
  body="$("${CURL[@]}" -w $'\n%{http_code}' "$TARGET/$1" 2>/dev/null)"
  code="$(printf '%s' "$body" | tail -1)"; body="$(printf '%s' "$body" | sed '$d')"; sleep "$SLEEP"
  if [ "$code" = 200 ] && printf '%s' "$body" | grep -qiE "$3"; then
    fail "$2 — POTVRZENO: $TARGET/$1 (obsah odpovida '$3')"
  elif [ "$code" = 200 ]; then
    warn "$2 — HTTP 200 na /$1 (prover obsah)"
  fi
}

sect "8) Zapomenute / citlive soubory a slozky"
info "Baseline neexistujici cesty: HTTP $BCODE (${BLEN}B) — podle toho se pozna 'dostupne'"
check_content ".git/config" "Expozice GIT repozitare" 'repositoryformatversion|\[core\]'
check_content ".git/HEAD"   "Expozice GIT repozitare" '^ref:'
check_content ".env"                 "Soubor .env" 'APP_|DB_|SECRET|PASSWORD|API_|KEY'
check_content ".env.local"           "Soubor .env.local" 'APP_|DB_|SECRET|PASSWORD|API_|KEY'
check_content ".env.production"      "Soubor .env.production" 'APP_|DB_|SECRET|PASSWORD|API_|KEY'
check_content "wp-config.php.bak"    "Zaloha wp-config" 'DB_PASSWORD|DB_NAME'
check_content "wp-config.php.save"   "Zaloha wp-config" 'DB_PASSWORD|DB_NAME'
check_content "wp-config.php~"       "Zaloha wp-config" 'DB_PASSWORD|DB_NAME'
check_content "phpinfo.php"          "phpinfo()" 'phpinfo\(\)|PHP Version'
check_content "info.php"             "phpinfo()" 'phpinfo\(\)|PHP Version'
for p in \
  backup.zip backup.tar.gz backup.sql database.sql db.sql dump.sql site.zip www.zip \
  .htaccess .htpasswd .DS_Store composer.json composer.lock package.json .npmrc \
  config.php configuration.php error_log debug.log server-status adminer.php \
  .vscode/settings.json .idea/workspace.xml storage/logs/laravel.log ; do
  check_path "$p" "Citlivy soubor"
done
# directory listing
for d in uploads/ files/ backup/ backups/ img/ images/ tmp/ .git/ ; do
  body="$("${CURL[@]}" "$TARGET/$d" 2>/dev/null)"
  printf '%s' "$body" | grep -qiE '<title>Index of /|Directory listing for' \
    && fail "Zapnuty vypis obsahu slozky (directory listing): $TARGET/$d"
  sleep "$SLEEP"
done

sect "9) Admin / prihlasovaci endpointy"
for p in admin/ administrator/ login wp-login.php wp-admin/ user/login \
         phpmyadmin/ pma/ .well-known/security.txt ; do
  check_path "$p" "Endpoint"
done

# =============================================================================
sect "10) WordPress (jen pokud detekovan)"
if [ "$IS_WP" = 1 ]; then
  U="$("${CURL[@]}" -w $'\n%{http_code}' "$TARGET/wp-json/wp/v2/users" 2>/dev/null)"
  UC="$(printf '%s' "$U" | tail -1)"; UB="$(printf '%s' "$U" | sed '$d')"
  if [ "$UC" = 200 ] && printf '%s' "$UB" | grep -qi '"slug"'; then
    fail "Enumerace uzivatelu: /wp-json/wp/v2/users vraci seznam uctu (jmena pro brute-force)"
    printf '%s' "$UB" | grep -oiE '"slug":"[^"]+"' | sed 's/^/       /' | head -10
  else info "REST enumerace uzivatelu nevraci seznam (dobre)"; fi
  X="$("${CURL[@]}" -o /dev/null -w '%{http_code}' "$TARGET/xmlrpc.php" 2>/dev/null)"
  case "$X" in 200|405|500) warn "xmlrpc.php je dostupny (HTTP $X) — vektor pro brute-force/amplifikaci; zvaz vypnuti";; esac
  check_content "readme.html" "WP verze v readme.html" 'Version [0-9]'
  sleep "$SLEEP"
else
  info "WordPress nedetekovan — preskoceno"
fi

# =============================================================================
sect "11) robots.txt / sitemap.xml / security.txt"
for f in robots.txt sitemap.xml .well-known/security.txt; do
  r="$("${CURL[@]}" -w $'\n%{http_code}' "$TARGET/$f" 2>/dev/null)"
  rc="$(printf '%s' "$r" | tail -1)"; rb="$(printf '%s' "$r" | sed '$d')"; sleep "$SLEEP"
  if [ "$rc" = 200 ]; then
    info "$f (HTTP 200):"; printf '%s\n' "$rb" | head -15 | sed 's/^/       /'
    [ "$f" = robots.txt ] && printf '%s' "$rb" | grep -qiE 'admin|backup|private|config' \
      && warn "robots.txt prozrazuje zajimave cesty (Disallow) — utocnik je precte take"
  fi
done

# =============================================================================
sect "SHRNUTI"
echo "  Zavaznych nalezu (FAIL): $FAIL"
echo "  Varovani        (WARN): $WARN"
echo "  Cil: $TARGET"
echo "  Vysledek ulozen do: $LOG"
echo
echo "  DALSI KROK: posli mi obsah souboru '$LOG' (nebo vystup z obrazovky)."
echo "  POZOR: pokud se v sekci 6 objevil skutecny tajny klic/heslo, PRED odeslanim ho zacernI"
echo "         a klic okamzite rotuj/zneplatni."
echo
echo "  Co tento skript ZAMERNE nedela: neposila utocne payloady do formularu,"
echo "  netestuje prihlaseni/hesla, nebrute-forcuje cesty, nedela DoS. To je"
echo "  invazivnejsi krok, ktery udelame az cileně a s rozmyslem."
