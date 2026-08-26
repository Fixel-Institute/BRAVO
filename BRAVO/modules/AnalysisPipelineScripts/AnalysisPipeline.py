import os, sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from filelock import Timeout, FileLock
from BRAVO import wsgi 
from Server import models

from modules.DataAnalysis import processBurstAnalysis

if __name__ == "__main__":
    if len(sys.argv) == 2:
        if sys.argv[1] == "ExtractSpectralFeaturesDuringSurvey":
            from modules.AnalysisPipelineScripts.ExtractSpectralFeaturesDuringSurvey import HandleRefreshAnalysis
            lock = FileLock(sys.argv[1] + ".lock")
            try:
                with lock.acquire(timeout=30):
                    HandleRefreshAnalysis()

            except Timeout:
                print("Lockfile Not Acquired before Timeout")
                
        elif sys.argv[1] == "ExtractSpectralFeaturesDuringStimulation":
            from modules.AnalysisPipelineScripts.ExtractSpectralFeaturesDuringStimulation import HandleRefreshAnalysis
            lock = FileLock(sys.argv[1] + ".lock")
            try:
                with lock.acquire(timeout=30):
                    HandleRefreshAnalysis()
                    
            except Timeout:
                print("Lockfile Not Acquired before Timeout")
    
    else:
        task_id = sys.argv[2]
        job = models.AsyncJob.find(uid=task_id)
        if job:
            if sys.argv[1] == "BurstAnalysis":
                recording = models.Recording.find(uid=job.recording_uid)
                participant_uid = job.metadata["config"]["ParticipantId"]
                userConfig = {**job.metadata["config"]}
                del userConfig["ParticipantId"]
                processBurstAnalysis(participant_uid, job.recording_uid, userConfig)
                job.state = "Completed"
                job.save()

            elif sys.argv[1] == "BIDSExport":
                from modules.BIDSExport.Gather import export_participant
                participant_uid = job.metadata["config"]["ParticipantId"]
                try:
                    exported = export_participant(participant_uid)
                    job.result_message = f"Exported {len(exported)} session(s) to BRAVOStorage/BIDS"
                    job.state = "Completed"
                except Exception as e:
                    job.result_message = str(e)
                    job.state = "Failed"
                job.save()
