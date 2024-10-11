/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { createRef, useState, memo } from "react";

import {
  Autocomplete,
  Grid,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Icon,
  IconButton,
  Tooltip,
} from "@mui/material";

import { createFilterOptions } from "@mui/material/Autocomplete";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";
import DropzoneUploader from "components/DropzoneUploader";

import { FaCopy } from "react-icons/fa";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

const filter = createFilterOptions();

function EditParticipantInfoView({show, participantInfo, onUpdate, onCancel, removeParticipant}) {
  const [controller, dispatch] = usePlatformContext();
  const { language, participant_uid } = controller;

  const [editParticipantInfo, setEditParticipantInfo] = useState({...participantInfo});
  
  return (
    <Dialog open={show} onClose={() => {
      onCancel();
      setEditParticipantInfo({...participantInfo});
    }}>
      
      <MDBox px={2} pt={2} display={"flex"} flexDirection={"row"} justifyContent={"center"} alignItems={"center"}>
        <MDTypography variant="h5">
          {"Edit Participant Information"}
        </MDTypography>
        <Tooltip title={"Click to Copy Participant Unique Identifier"}>
          <IconButton onClick={() => {
            navigator.clipboard.writeText(participant_uid);
          }}>
            <FaCopy />
          </IconButton>
        </Tooltip>
      </MDBox>
      <DialogContent>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <TextField
              variant="standard"
              margin="dense" id="name"
              value={editParticipantInfo.name}
              onChange={(event) => setEditParticipantInfo({...editParticipantInfo, name: event.target.value})}
              label={"Participant Name"} type="text"
              fullWidth
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              variant="standard"
              margin="dense" id="diagnosis"
              value={editParticipantInfo.diagnosis}
              onChange={(event) => setEditParticipantInfo({...editParticipantInfo, diagnosis: event.target.value})}
              label={"Diagnosis"} type="text"
              fullWidth
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <Autocomplete selectOnFocus clearOnBlur
              renderInput={(params) => (
                <TextField {...params} variant="standard" placeholder={"Select Sex/Gender (Optional)"} />
              )}
              isOptionEqualToValue={(option, value) => {
                return option === value;
              }}
              renderOption={(props, option) => <li {...props}>{option}</li>}
              value={editParticipantInfo.sex ? editParticipantInfo.sex : "Other"}
              options={["Male", "Female", "Other"]}
              onChange={(event, newValue) => setEditParticipantInfo({...editParticipantInfo, sex: newValue})}
            />
          </Grid>
          <Grid item xs={12}>
            <Autocomplete 
              selectOnFocus clearOnBlur multiple
              renderInput={(params) => (
                <TextField
                  {...params}
                  variant="standard" id="tags"
                  placeholder={dictionary.ParticipantOverview.TagNames[language]}
                />
              )}
              filterOptions={(options, params) => {
                const filtered = filter(options, params);
                const { inputValue } = params;

                // Suggest the creation of a new value
                const isExisting = options.some((option) => inputValue === option.title);
                if (inputValue !== '' && !isExisting) {
                  filtered.push({
                    inputValue,
                    title: `Add "${inputValue}"`,
                  });
                }
                return filtered;
              }}
              getOptionLabel={(option) => {
                if (typeof option === 'string') {
                  return option;
                }
                if (option.inputValue) {
                  return option.inputValue;
                }
                return option.title;
              }}
              isOptionEqualToValue={(option, value) => {
                return option.value === value.value;
              }}
              renderOption={(props, option) => <li {...props}>{option.title}</li>}

              options={[]}
              value={editParticipantInfo.tags}
              onChange={(event, newValue) => setEditParticipantInfo({...editParticipantInfo, tags: newValue})}
            />
          </Grid>
          <Grid item xs={12} sx={{display: "flex", justifyContent: "space-between"}}>
            <MDBox style={{paddingLeft: 5}}>
              <MDButton color={"error"} 
                onClick={() => removeParticipant()}
              >
                Delete
              </MDButton>
            </MDBox>
            <MDBox style={{marginLeft: "auto", paddingRight: 5}}>
              <MDButton color={"secondary"} style={{marginLeft: 10}} 
                onClick={onCancel}
              >
                Cancel
              </MDButton>
              <MDButton color={"info"} 
                onClick={() => onUpdate(editParticipantInfo)} style={{marginLeft: 10}}
              >
                Update
              </MDButton>
            </MDBox>
          </Grid>
        </Grid>
      </DialogContent>
    </Dialog>
  )
}

export default memo(EditParticipantInfoView);