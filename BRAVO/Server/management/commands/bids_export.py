import time

from django.core.management.base import BaseCommand, CommandError

from Server.models import Participant
from modules.BIDSExport.Gather import export_participant


class Command(BaseCommand):
    help = (
        "Export participant(s) straight to BIDS, bypassing the API/AsyncJob "
        "queue (ExportBIDS in DataFilter.py) - for local bulk testing against "
        "a large dataset without the web stack running."
    )

    def add_arguments(self, parser):
        parser.add_argument("participant_uid", nargs="*", help="Participant uid(s) to export")
        parser.add_argument("--all", action="store_true", help="Export every participant in the database")

    def handle(self, *args, **options):
        if options["all"]:
            uids = list(Participant.objects.values_list("uid", flat=True))
        else:
            uids = options["participant_uid"]
        if not uids:
            raise CommandError("Provide one or more participant uids, or --all")

        failures = []
        for i, uid in enumerate(uids, 1):
            self.stdout.write(f"[{i}/{len(uids)}] Exporting {uid}...")
            start = time.time()
            try:
                exported = export_participant(uid)
                self.stdout.write(self.style.SUCCESS(
                    f"  OK - {len(exported)} session(s) in {time.time() - start:.1f}s"
                ))
            except Exception as e:
                failures.append((uid, str(e)))
                self.stdout.write(self.style.ERROR(f"  FAILED - {e}"))

        if failures:
            self.stdout.write(self.style.ERROR(f"\n{len(failures)}/{len(uids)} participant(s) failed:"))
            for uid, err in failures:
                self.stdout.write(f"  {uid}: {err}")
            raise CommandError(f"{len(failures)} export(s) failed")

        self.stdout.write(self.style.SUCCESS(f"\nAll {len(uids)} participant(s) exported."))
