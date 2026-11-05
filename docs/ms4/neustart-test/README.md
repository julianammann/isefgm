# Neustart- und Absturztest Scheduler (#58)

Nachweis für das Akzeptanzkriterium „Container starten nach Neustart automatisch“ aus #58 (Q-02, QZ-05).

Der Lauf fand am 04.11.2026 von 21:32:48 bis 21:33:04 UTC statt, mit dem lokalen Compose-Stack (`compose.yaml` mit `compose.override.yaml`) unter Docker Desktop auf macOS. Die Images sind aus dem Stand `d85841c` gebaut (`docker compose up --build -d`). Ein Skript hat jeden Befehl mit Zeitstempel in UTC und seiner unveränderten Ausgabe protokolliert. Das Protokoll unten ist diese Ausgabe.

## Ergebnis

| Schritt | Beleg im Protokoll | Ergebnis |
| --- | --- | --- |
| Absturz: Scheduler-Prozess (PID 7) um 21:32:48 mit `SIGKILL` beendet | `docker events` zeigt `die exitCode=137` und in derselben Sekunde `start`. `restarts` steigt von 0 auf 1, `started` springt von 21:23:31 auf 21:32:48. | Scheduler um 21:32:49 neu gestartet, Lauf erfolgreich abgeschlossen |
| Neustart: `docker desktop restart` um 21:32:50 | `docker events` zeigt um 21:32:58 `start` für db, api, scheduler, frontend und mailpit, ohne `docker compose up`. `started` aller fünf Dienste springt auf 21:32:58. | live, ready und Login-Seite antworten mit 200, Scheduler um 21:32:59 gestartet, Lauf erfolgreich abgeschlossen |

migrate bleibt nach beiden Schritten mit Exit-Code 0 beendet, `started` bleibt bei 21:22:48. So ist es mit `restart: "no"` vorgesehen.

Der Zähler `restarts` steht nach dem Neustart von Docker wieder auf 0. Den Neustart belegen die neuen Startzeiten und die `start`-Ereignisse.

Abschnitt 4 listet alle Scheduler-Starts im Container-Log. Die ersten drei stammen aus dem ersten, manuell protokollierten Lauf (Kommentar in #58).

## Grenzen

- Geprüft nur lokal mit Docker Desktop, nicht auf dem Server und nicht mit einem echten Neustart des Rechners.
- Die Stopp-Ereignisse beim Herunterfahren von Docker fehlen. `docker events` lieferte nach dem Neustart nur die `start`-Ereignisse.
- Docker startete alle fünf Dienste in derselben Sekunde, ohne die Reihenfolge aus `depends_on`. Den Fall, dass die Datenbank beim ersten Scheduler-Lauf noch nicht bereit ist, deckt der Test nicht ab.

## Protokoll

```text

==================== 0. Umgebung ====================

[2026-11-04T21:32:48Z] $ git rev-parse --short HEAD
d85841c

[2026-11-04T21:32:48Z] $ docker version --format 'Docker Engine {{.Server.Version}} ({{.Server.Os}}/{{.Server.Arch}})'
Docker Engine 29.9.2 (linux/arm64)

[2026-11-04T21:32:48Z] $ docker desktop version
Docker Desktop CLI plugin version: 4.98.0

[2026-11-04T21:32:48Z] $ docker compose ps -a --format 'table {{.Service}}\t{{.Status}}'
SERVICE     STATUS
api         Up 9 minutes (healthy)
db          Up 9 minutes (healthy)
frontend    Up 9 minutes (healthy)
mailpit     Up 9 minutes (healthy)
migrate     Exited (0) 9 minutes ago
scheduler   Up 9 minutes

==================== 1. Ausgangslage ====================

[2026-11-04T21:32:48Z] $ for c in db migrate api scheduler frontend mailpit; do docker inspect -f "$c	{{.State.Status}}	exit={{.State.ExitCode}}	restarts={{.RestartCount}}	started={{.State.StartedAt}}	health={{if .State.Health}}{{.State.Health.Status}}{{else}}-{{end}}" isefgm-$c-1; done
db	running	exit=0	restarts=0	started=2026-11-04T21:23:31.126623792Z	health=healthy
migrate	exited	exit=0	restarts=0	started=2026-11-04T21:22:48.096095919Z	health=-
api	running	exit=0	restarts=0	started=2026-11-04T21:23:31.125016542Z	health=healthy
scheduler	running	exit=0	restarts=0	started=2026-11-04T21:23:31.122861583Z	health=-
frontend	running	exit=0	restarts=0	started=2026-11-04T21:23:31.120727667Z	health=healthy
mailpit	running	exit=0	restarts=0	started=2026-11-04T21:23:31.119022375Z	health=healthy

[2026-11-04T21:32:48Z] $ curl -sS --max-time 5 -o /dev/null -w 'live  %{http_code}\n' http://localhost:8000/api/v1/health/live; curl -sS --max-time 5 -o /dev/null -w 'ready %{http_code}\n' http://localhost:8000/api/v1/health/ready; curl -sS --max-time 5 -o /dev/null -w 'login %{http_code}\n' http://localhost:3000/login
live  200
ready 200
login 200

==================== 2. Absturz: Scheduler-Prozess im Container mit SIGKILL beenden ====================

[2026-11-04T21:32:48Z] $ docker compose exec -T scheduler python -c "import os, signal
for p in filter(str.isdigit, os.listdir('/proc')):
    cmd = open(f'/proc/{p}/cmdline', 'rb').read().replace(b'\\0', b' ')
    if cmd.startswith(b'python -m giftmanager.scheduler'):
        print('kill -9', p, cmd.decode().strip())
        os.kill(int(p), signal.SIGKILL)"
kill -9 7 python -m giftmanager.scheduler
[2026-11-04T21:32:48Z] ok after 0s: scheduler laeuft wieder, RestartCount > 0
[2026-11-04T21:32:50Z] ok after 1s: neuer Scheduler-Lauf abgeschlossen

[2026-11-04T21:32:50Z] $ docker events --since 1793827968 --until $(date +%s) --filter type=container --filter label=com.docker.compose.project=isefgm --filter event=kill --filter event=die --filter event=stop --filter event=start --filter event=restart --format '{{.Time}} {{.Actor.Attributes.name}} {{.Action}}{{with index .Actor.Attributes "exitCode"}} exitCode={{.}}{{end}}' | while read t rest; do echo "$(date -u -r $t '+%Y-%m-%dT%H:%M:%SZ') $rest"; done
2026-11-04T21:32:48Z isefgm-scheduler-1 die exitCode=137
2026-11-04T21:32:48Z isefgm-scheduler-1 start

[2026-11-04T21:32:50Z] $ for c in db migrate api scheduler frontend mailpit; do docker inspect -f "$c	{{.State.Status}}	exit={{.State.ExitCode}}	restarts={{.RestartCount}}	started={{.State.StartedAt}}	health={{if .State.Health}}{{.State.Health.Status}}{{else}}-{{end}}" isefgm-$c-1; done
db	running	exit=0	restarts=0	started=2026-11-04T21:23:31.126623792Z	health=healthy
migrate	exited	exit=0	restarts=0	started=2026-11-04T21:22:48.096095919Z	health=-
api	running	exit=0	restarts=0	started=2026-11-04T21:23:31.125016542Z	health=healthy
scheduler	running	exit=0	restarts=1	started=2026-11-04T21:32:48.90045955Z	health=-
frontend	running	exit=0	restarts=0	started=2026-11-04T21:23:31.120727667Z	health=healthy
mailpit	running	exit=0	restarts=0	started=2026-11-04T21:23:31.119022375Z	health=healthy

[2026-11-04T21:32:50Z] $ docker compose logs --no-log-prefix --since 1793827968 scheduler | grep -E 'Scheduler started|Running job|executed successfully|raised an exception'
2026-11-04T21:32:49.450527Z [info     ] Scheduler started              [apscheduler.scheduler]
2026-11-04T21:32:49.450780Z [info     ] Running job "run_once (trigger: interval[0:05:00], next run at: 2026-11-04 21:37:49 UTC)" (scheduled at 2026-11-04 21:32:49.438672+00:00) [apscheduler.executors.default]
2026-11-04T21:32:49.494977Z [info     ] Job "run_once (trigger: interval[0:05:00], next run at: 2026-11-04 21:37:49 UTC)" executed successfully [apscheduler.executors.default]

==================== 3. Neustart von Docker Desktop ====================

[2026-11-04T21:32:50Z] $ docker desktop restart --timeout 300
✓ Starting Docker Desktop
[2026-11-04T21:32:59Z] ok after 0s: Docker Engine antwortet
[2026-11-04T21:33:04Z] ok after 3s: db, api, scheduler, frontend, mailpit laufen, api healthy
[2026-11-04T21:33:04Z] ok after 0s: erster Scheduler-Lauf nach dem Neustart abgeschlossen

[2026-11-04T21:33:04Z] $ docker desktop status
Name                Value
Status              running
SessionID           c63faad7-b850-45de-a801-444c6d3bf421

[2026-11-04T21:33:04Z] $ docker events --since 1793827970 --until $(date +%s) --filter type=container --filter label=com.docker.compose.project=isefgm --filter event=kill --filter event=die --filter event=stop --filter event=start --filter event=restart --format '{{.Time}} {{.Actor.Attributes.name}} {{.Action}}{{with index .Actor.Attributes "exitCode"}} exitCode={{.}}{{end}}' | while read t rest; do echo "$(date -u -r $t '+%Y-%m-%dT%H:%M:%SZ') $rest"; done
2026-11-04T21:32:58Z isefgm-mailpit-1 start
2026-11-04T21:32:58Z isefgm-api-1 start
2026-11-04T21:32:58Z isefgm-scheduler-1 start
2026-11-04T21:32:58Z isefgm-db-1 start
2026-11-04T21:32:58Z isefgm-frontend-1 start

[2026-11-04T21:33:04Z] $ for c in db migrate api scheduler frontend mailpit; do docker inspect -f "$c	{{.State.Status}}	exit={{.State.ExitCode}}	restarts={{.RestartCount}}	started={{.State.StartedAt}}	health={{if .State.Health}}{{.State.Health.Status}}{{else}}-{{end}}" isefgm-$c-1; done
db	running	exit=0	restarts=0	started=2026-11-04T21:32:58.235433584Z	health=healthy
migrate	exited	exit=0	restarts=0	started=2026-11-04T21:22:48.096095919Z	health=-
api	running	exit=0	restarts=0	started=2026-11-04T21:32:58.228337875Z	health=healthy
scheduler	running	exit=0	restarts=0	started=2026-11-04T21:32:58.220058875Z	health=-
frontend	running	exit=0	restarts=0	started=2026-11-04T21:32:58.218112792Z	health=healthy
mailpit	running	exit=0	restarts=0	started=2026-11-04T21:32:58.219387125Z	health=healthy

[2026-11-04T21:33:04Z] $ curl -sS --max-time 5 -o /dev/null -w 'live  %{http_code}\n' http://localhost:8000/api/v1/health/live; curl -sS --max-time 5 -o /dev/null -w 'ready %{http_code}\n' http://localhost:8000/api/v1/health/ready; curl -sS --max-time 5 -o /dev/null -w 'login %{http_code}\n' http://localhost:3000/login
live  200
ready 200
login 200

[2026-11-04T21:33:04Z] $ docker compose logs --no-log-prefix --since 1793827970 scheduler | grep -E 'Scheduler started|Running job|executed successfully|raised an exception'
2026-11-04T21:32:59.589846Z [info     ] Scheduler started              [apscheduler.scheduler]
2026-11-04T21:32:59.590148Z [info     ] Running job "run_once (trigger: interval[0:05:00], next run at: 2026-11-04 21:37:59 UTC)" (scheduled at 2026-11-04 21:32:59.550945+00:00) [apscheduler.executors.default]
2026-11-04T21:32:59.699441Z [info     ] Job "run_once (trigger: interval[0:05:00], next run at: 2026-11-04 21:37:59 UTC)" executed successfully [apscheduler.executors.default]

==================== 4. Alle Scheduler-Starts im Container-Log ====================

[2026-11-04T21:33:04Z] $ docker compose logs --no-log-prefix scheduler | grep 'Scheduler started'
2026-11-04T21:22:49.745575Z [info     ] Scheduler started              [apscheduler.scheduler]
2026-11-04T21:23:11.806526Z [info     ] Scheduler started              [apscheduler.scheduler]
2026-11-04T21:23:32.019109Z [info     ] Scheduler started              [apscheduler.scheduler]
2026-11-04T21:32:49.450527Z [info     ] Scheduler started              [apscheduler.scheduler]
2026-11-04T21:32:59.589846Z [info     ] Scheduler started              [apscheduler.scheduler]

[2026-11-04T21:33:04Z] Ende
```
