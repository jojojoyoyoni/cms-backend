"""One-shot or looping SLA scan. Usage:
    python manage.py run_sla_checks              # single pass
    python manage.py run_sla_checks --loop 300   # every 5 minutes
"""
import time
import traceback

from django.core.management.base import BaseCommand

from apps.cases.escalation import run_sla_pass


class Command(BaseCommand):
    help = "Detect SLA breaches and escalate cases"

    def add_arguments(self, parser):
        parser.add_argument("--loop", type=int, default=0, metavar="SECONDS",
                            help="Keep running every N seconds (0 = run once)")

    def handle(self, *args, **opts):
        interval = opts["loop"]
        while True:
            try:
                stats = run_sla_pass()
                self.stdout.write(self.style.SUCCESS(
                    f"[SLA] scanned={stats['scanned']} "
                    f"created={stats['created']} auto_resolved={stats['auto_resolved']}"
                ))
            except Exception:
                self.stderr.write(traceback.format_exc())
            if not interval:
                break
            time.sleep(interval)