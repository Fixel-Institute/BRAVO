import os, subprocess
from pathlib import Path
from celery import shared_task 

BASE_DIR = Path(__file__).resolve().parent.parent

@shared_task
def ProcessUploadQueue():
    print("Check Upload")
    subprocess.call(["bash", os.path.join(BASE_DIR, 'ProcessingQueueJob.sh')])

@shared_task
def ProcessAnalysisQueue():
    print("Check Analysis")
    subprocess.call(["bash", os.path.join(BASE_DIR, 'AnalysisProcessingJob.sh')])
  