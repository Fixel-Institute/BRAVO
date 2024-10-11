import os
from uuid import uuid4

from neomodel import StructuredNode, StringProperty, ArrayProperty, FloatProperty, JSONProperty, IntegerProperty, Relationship, RelationshipFrom, RelationshipTo, db

from .HelperFunctions import current_time

class SourceFile(StructuredNode):
    uid = StringProperty(default=uuid4)
    name = StringProperty()
    type = StringProperty()
    date = FloatProperty(default=current_time)
    file_pointer = StringProperty()
    metadata = JSONProperty()

    queue = RelationshipFrom("ProcessingQueue", "FILE_TO_PROCESS")
    uploader = RelationshipFrom(".User.PlatformUser", "UPLOADED_FILE")
    experiment = RelationshipFrom(".Participant.Experiment", "HAS_SOURCE_FILE")

    device = RelationshipTo(".Device.BaseDevice", "RECORDED_WITH")
    
    recordings = RelationshipTo(".Recording.Recording", "SOURCE_OF_RECORDING")
    therapies = RelationshipTo(".Therapy.Therapy", "SOURCE_OF_THERAPY")
    events = RelationshipTo(".Event.BaseEvent", "SOURCE_OF_EVENT")

    def getQueueInfo(self):
        if len(self.queue) == 0:
            return { "uid": self.uid, "filename": self.name, "job_id": "", "job_type": "",
                "since": self.date, "state": "Unknown", "descriptor": "",
            }
        
        queue = self.queue[0]
        return { "uid": queue.uid, "filename": self.name, "job_id": queue.job_id, "job_type": queue.job_type,
            "since": queue.date, "state": queue.status, "descriptor": queue.result,
        }
    
    def purge(self):
        for therapy in self.therapies:
            therapy.purge()
        
        for event in self.events:
            event.purge()
        
        for recording in self.recordings:
            recording.purge()

        for queue in self.queue:
            queue.delete()
        
        try:
            os.remove(self.file_pointer)
        except:
            pass
        self.delete()
        
class ProcessingQueue(StructuredNode):
    uid = StringProperty(default=uuid4)
    job_id = StringProperty()
    job_type = StringProperty()
    date = FloatProperty(default=current_time)
    status = StringProperty()
    result = StringProperty()
    
    cache_file = RelationshipTo("SourceFile", "FILE_TO_PROCESS")

    def uploadedBy(user):
        uid = f"'{user.user_id}'"
        results, _ = db.cypher_query(f"MATCH (a:PlatformUser {{user_id: {uid}}})-[:UPLOADED_FILE]->(:SourceFile)-[:FILE_TO_PROCESS]->(:ProcessingQueue) RETURN a", resolve_objects=True)
        return [row[0] for row in results]
    