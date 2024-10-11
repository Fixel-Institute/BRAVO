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
Therapy Models
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from neomodel import StructuredNode, StringProperty, FloatProperty, ArrayProperty, IntegerProperty, Relationship, RelationshipTo, RelationshipFrom

class Therapy(StructuredNode):
    name = StringProperty(max_length=128)
    type = StringProperty(max_length=128)
    date = FloatProperty()

    source_file = RelationshipFrom(".SourceFile.SourceFile", "SOURCE_OF_THERAPY")

    def purge(self):
        self.delete()

class Medication(Therapy):
    medication = StringProperty()
    dosage = FloatProperty()
    frequency = StringProperty()

class ElectricalTherapy(Therapy):
    group_name = StringProperty()
    group_id = StringProperty()
    stimulation_type = StringProperty()
    
    settings = Relationship("ElectricalStimulation", "HAS_ELECTRICAL_STIMULATION")

    def purge(self):
        for setting in self.settings:
            setting.delete()
        self.delete()

    def getInfo(self):
        return {
            "Name": self.name,
            "GroupName": self.group_name,
            "GroupId": self.group_id,
            "Type": self.type,
            "StimulationType": self.stimulation_type,
            "Date": self.date,
            "TherapyConfigurations": [setting.getInfo() for setting in self.settings],
        }

class AdaptiveTherapy(ElectricalTherapy):
    pass

class MedtronicPerceptAdaptiveTherapy(AdaptiveTherapy):
    pass

class ElectricalStimulation(StructuredNode):
    electrode = Relationship(".Device.Electrode", "USE_ELECTRODE")
    contact = ArrayProperty(IntegerProperty())
    return_contact = ArrayProperty(IntegerProperty())
    amplitude = ArrayProperty(FloatProperty())
    amplitude_unit = StringProperty()
    pulsewidth = FloatProperty()
    pulsewidth_unit = StringProperty()
    frequency = FloatProperty()
    cycling = FloatProperty()
    cycling_period = FloatProperty()

    waveform = StringProperty() # This needs to be implemented as a method later, typical options being passive or active, cathode/anode etc.

    def getInfo(self):
        Electrode = self.electrode.get().getInfo()
        return {
            "LeadName": Electrode["custom_name"],
            "Contact": [Electrode["channel_names"][i] for i in self.contact],
            "ReturnContact": [Electrode["channel_names"][i] for i in self.return_contact if i >= 0],
            "Amplitude": self.amplitude,
            "AmplitudeUnit": self.amplitude_unit,
            "Pulsewidth": self.pulsewidth,
            "PulsewidthUnit": self.pulsewidth_unit,
            "Pulsewidth": self.pulsewidth,
            "PulsewidthUnit": self.pulsewidth_unit,
            "Frequency": self.frequency,
            "Cycling": self.cycling,
            "CyclingPeriod": self.cycling_period 
        }