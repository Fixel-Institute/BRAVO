import os, sys
BRAVO_Path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BRAVO_Path)

from BRAVO import wsgi
from Server import models
import subprocess
import psutil
import time

USE_SLURM = os.environ.get('USE_SLURM', 'FALSE') == 'TRUE'
SLURM_JOB_PATH = os.path.join(BRAVO_Path, "modules", "AsyncJobScheduler")

AsyncJobScripts = {
    "BurstAnalysis": "/modules/AnalysisPipelineScripts/AnalysisPipeline.py BurstAnalysis ${JOB_ARGS}",
    "FitbitRefresh": "/modules/Fitbit/FitbitDataUpdateService.py ${JOB_ARGS}",
    "ExtractSpectralFeaturesDuringStimulation": "/modules/AnalysisPipelineScripts/AnalysisPipeline.py ExtractSpectralFeaturesDuringStimulation",
    "ExtractSpectralFeaturesDuringSurvey": "/modules/AnalysisPipelineScripts/AnalysisPipeline.py ExtractSpectralFeaturesDuringSurvey",
    "BIDSExport": "/modules/AnalysisPipelineScripts/AnalysisPipeline.py BIDSExport ${JOB_ARGS}",
}

def ScheduleSlurmJob(requester, recording_uid, script_name, config, refresh=False):
    existing_job = models.AsyncJob.find(recording_uid=recording_uid, requester=requester, metadata__script_name=script_name, metadata__config=config)
    if existing_job:
        if refresh:
            state = CheckJobStatus(existing_job)
            if not state["State"] == "Completed":
                return existing_job
        else:
            return existing_job

    job = models.AsyncJob.create(
        name="BRAVO_Processing_Schedule",
        type="SLURM" if USE_SLURM else "LOCAL",
        recording_uid=recording_uid,
        result_message="",
        requester=requester,
        metadata={
            "script_name": script_name,
            "config": config
        }
    )

    with open(os.path.join(SLURM_JOB_PATH, "sjob.sh"), 'r') as f:
        sbatch_script = f.read()
    
    sbatch_script = sbatch_script.replace("${SLURM_JOB_NAME}", job.uid)
    sbatch_script = sbatch_script.replace("${SLURM_WORKING_DIR}", SLURM_JOB_PATH)
    sbatch_script = sbatch_script.replace("${PYTHON_ENV}", os.path.dirname(BRAVO_Path) + "/.venv/bin/activate")
    sbatch_script = sbatch_script.replace("${SLURM_JOB_SCRIPT}", BRAVO_Path + AsyncJobScripts[script_name])
    sbatch_script = sbatch_script.replace("${JOB_ARGS}", job.uid)

    with open(os.path.join(SLURM_JOB_PATH, job.uid + ".sh"), 'w+') as f:
        f.write(sbatch_script)

    if USE_SLURM:
        result = subprocess.run("sbatch " + os.path.join(SLURM_JOB_PATH, job.uid + ".sh"), capture_output=True, text=True, shell=True)
        job.metadata["slurm_job_id"] = result.stdout.strip().split(" ")[-1]
        job.save()
    else:
        process = subprocess.Popen(["bash", os.path.join(SLURM_JOB_PATH, job.uid + ".sh")])
        job.metadata["pid"] = process.pid
        while True:
            try:
                ps_proc = psutil.Process(job.metadata["pid"])
                # PIDs get recycled by the OS - record the process's actual
                # start time alongside it so a later liveness check
                # (CheckJobStatus) can tell "still this job" apart from "some
                # unrelated process now sitting at the same PID", instead of
                # trusting the bare PID number forever.
                job.metadata["pid_create_time"] = ps_proc.create_time()
                job.state = "Running"
                job.save()
                break
            except psutil.Error:
                job.state = "Pending"
                job.save()
            time.sleep(1)
            
    return job

def CheckJobStatus(job):
    if job.type == "LOCAL":
        try:
            ps_proc = psutil.Process(job.metadata["pid"])
            # A PID alone isn't proof this job's process is still running -
            # the OS recycles PIDs, so a long-finished job's PID can later
            # get reassigned to some unrelated process that's simply alive
            # at the moment of this check. Confirming create_time() matches
            # what was recorded when this job was actually launched is what
            # tells the two apart - found via a real stuck "Running" BIDS
            # export job whose PID had been reused, which meant
            # ScheduleSlurmJob's refresh=True re-export never actually
            # re-ran (it kept handing back the same stale job instead).
            if ps_proc.create_time() != job.metadata.get("pid_create_time"):
                raise psutil.NoSuchProcess(job.metadata["pid"])
            job.state = "Running"
            job.save()

        except psutil.Error:
            job.state = "Completed"
            job.save()

    elif job.type == "SLURM":
        format_str = "\"%.18i|%.9P|%.20j|%.8u|%.2t|%.10M|%.6D|%.30R\""
        result = subprocess.run("squeue -j " + job.metadata["slurm_job_id"] + " --noheader --format " + format_str, capture_output=True, text=True, shell=True)
        if len(result.stdout.strip()) == 0:
            job.state = "Completed"
            job.save()
        else:
            result = result.stdout.strip().split("|")
            job.state = result[4].strip()
            job.save()

    return job.get_info()

if __name__ == "__main__":
    pass