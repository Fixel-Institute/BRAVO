import os
from uuid import uuid4

from neomodel import StructuredNode, StringProperty, ArrayProperty, FloatProperty, JSONProperty, IntegerProperty, Relationship, db

from .HelperFunctions import current_time

class SourceFile(StructuredNode):
    uid = StringProperty(unique_index=True, default=uuid4)
    name = StringProperty()
    date = FloatProperty(default=current_time)
    file_pointer = StringProperty()
    metadata = JSONProperty()

    uploader = Relationship(".User.PlatformUser", "UPLOADED_BY")
    
    participant = Relationship(".Participant.Participant", "UPLOADED_FOR")
    recordings = Relationship(".Recording.Recording", "SOURCE_OF_RECORDING")
    therapies = Relationship(".Therapy.Therapy", "SOURCE_OF_THERAPY")
    events = Relationship(".Event.BaseEvent", "SOURCE_OF_EVENT")

    def getInfo(self):
        return {
            "uid": self.uid,
            "name": self.name,
            "metadata": self.metadata,
            "date": self.date
        }

    def getAllSessionFilesForParticipant(participant):
        uid = f"'{participant.uid}'"
        results, _ = db.cypher_query(f"MATCH (a:SourceFile)-[:UPLOADED_FOR]->(:Participant {{uid: {uid}}}) RETURN a", resolve_objects=True)
        return [row[0] for row in results]

    def purge(self):
        for therapy in self.therapies:
            therapy.purge()
        for event in self.events:
            event.purge()
        for recording in self.recordings:
            recording.purge()
        
        results, _ = db.cypher_query(f"MATCH (a:ProcessingQueue)-[:FILE_TO_PROCESS]->(:SourceFile {{uid: '{self.uid}'}}) RETURN a", resolve_objects=True)
        for row in results:
            row[0].purge()

        try:
            os.remove(self.file_pointer)
        except:
            pass 
        self.delete()

class ProcessingQueue(StructuredNode):
    uid = StringProperty(unique_index=True, default=uuid4)
    job_id = StringProperty()
    job_type = StringProperty()
    date = FloatProperty(default=current_time)
    status = StringProperty()
    result = StringProperty()
    
    cache_file = Relationship("SourceFile", "FILE_TO_PROCESS")

    def uploadedBy(user_id):
        uid = f"'{user_id}'"
        results, _ = db.cypher_query(f"MATCH (a:ProcessingQueue)-[:FILE_TO_PROCESS]->(:SourceFile)-[:UPLOADED_BY]->(:PlatformUser {{user_id: {uid}}}) RETURN a", resolve_objects=True)
        return [row[0] for row in results]
    
    def purge(self):
        self.delete()