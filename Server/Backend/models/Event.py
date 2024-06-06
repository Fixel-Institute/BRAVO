""""""
"""
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2024 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""
"""
Event Nodes
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from uuid import uuid4

from neomodel import StructuredNode, StringProperty, FloatProperty, Relationship, db

class BaseEvent(StructuredNode):
    uid = StringProperty(unique_index=True, default=uuid4)
    name = StringProperty(max_length=128)
    type = StringProperty(max_length=128)
    date = FloatProperty(required=True)

    ### All these could be empty, or could all be filled with data, I don't have a good design yet. 
    scales = Relationship("BaseScale", "WITH_SCALE") # Scale Event
    data = Relationship(".Recording.Recording", "WITH_DATA") # Recording Event
    therapy = Relationship(".Therapy.Therapy", "WITH_THERAPY") # Change Therapy Event

    def purge(self):
        for scale in self.scales:
            scale.purge()
        for data in self.data:
            data.purge()
        for therapy in self.therapy:
            therapy.purge()
        self.delete()

class TherapyModification(BaseEvent):
    new_group = StringProperty()
    old_group = StringProperty()
    device = StringProperty()

class BaseScale(StructuredNode):
    uid = StringProperty(unique_index=True, default=uuid4)
    name = StringProperty(max_length=128)
    date = FloatProperty(required=True)

    def setScale(self, scales):
        if not type(scales) == dict:
            raise Exception("Scale must be a dictionary")
        
        scaleKeys = scales.keys()
        for key, _ in self.__all_properties__:
            if key in scaleKeys:
                setattr(self, key, scales[key])

    def getScale(self):
        scale = dict()
        labels = dict(self.__all_properties__)
        for key in labels.keys():
            if labels[key].label:
                scale[key] = {"label": labels[key].label, "value": getattr(self, key, None)}
            else:
                scale[key] = getattr(self, key, None)
        return scale
    
    def getScalesFromParticipant(participant, event=None, scale=None):
        uid = f"'{participant.uid}'"
        eventSelector = f" {{type: '{event}'}}"if event else ""
        scaleSelector = f" {{type: '{scale}'}}"if scale else ""
        results, _ = db.cypher_query(f"MATCH (a:Participant {{uid: {uid}}})-[:HAS_EVENT]->(:BaseEvent{eventSelector})-[:WITH_SCALE]->(scales:BaseScale{scaleSelector}) RETURN scales", resolve_objects=True)
        return [row[0] for row in results]

    def purge(self):
        self.delete()

class UnifiedParkinsonsDiseaseRatingScalePartIII(BaseScale):
    type = StringProperty(default="UPDRS Part-III")

    q18 = FloatProperty(label="Speech")
    q19 = FloatProperty(label="Facial Expression")
    q20fcl = FloatProperty(label="Head Resting Tremor")
    q20rh = FloatProperty(label="Right Hand Resting Tremor")
    q20lh = FloatProperty(label="Left Hand Resting Tremor")
    q20rl = FloatProperty(label="Right Leg Resting Tremor")
    q20ll = FloatProperty(label="Left Leg Resting Tremor")
    q21rh = FloatProperty(label="Right Hand Postural Tremor")
    q21lh = FloatProperty(label="Left Hand Postural Tremor")
    q22n = FloatProperty(label="Neck Rigidity")
    q22rue = FloatProperty(label="Right Upper Extremity Rigidity")
    q22lue = FloatProperty(label="Left Upper Extremity Rigidity")
    q22rle = FloatProperty(label="Right Lower Extremity Rigidity")
    q22lle = FloatProperty(label="Left Lower Extremity Rigidity")
    q23rh = FloatProperty(label="Right Finger Tapping")
    q23lh = FloatProperty(label="Left Finger Tapping")
    q24rh = FloatProperty(label="Right Hand Movement")
    q24lh = FloatProperty(label="Left Hand Movement")
    q25rh = FloatProperty(label="Right Hand Rapid Alternative Movement")
    q25lh = FloatProperty(label="Left Hand Rapid Alternative Movement")
    q26rl = FloatProperty(label="Right Leg Agility")
    q26ll = FloatProperty(label="Left Leg Agility")
    q27 = FloatProperty(label="Arising from Chair")
    q28 = FloatProperty(label="Posture")
    q29 = FloatProperty(label="Gait")
    q30 = FloatProperty(label="Postural Stability")
    q31 = FloatProperty(label="Body Bradykinesia and Hypokinesia")
