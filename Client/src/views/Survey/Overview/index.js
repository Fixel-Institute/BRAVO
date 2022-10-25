import { useEffect, useState } from "react";

import {
  Card,
  Grid,
  Dialog,
  DialogContent,
  DialogActions,
  TextField
} from "@mui/material";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";
import SurveyTable from "components/Tables/SurveyTable";

import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

export default function SurveyList() {
  const [controller, dispatch] = usePlatformContext();
  const { user, language } = controller;

  const [filteredPatients, setFilteredPatients] = useState([]);
  const [filterOptions, setFilterOptions] = useState({});
  const [surveys, setSurveys] = useState([]);
  const [newSurveyDialog, setNewSurveyDialog] = useState({surveyName: "", state: false});
  const [alert, setAlert] = useState(null);

  useEffect(() => {
    SessionController.query("/api/queryAvailableSurveys").then((response) => {
      if (response.status == 200) {
        setSurveys(response.data);
        console.log(response.data)
      }
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }, []);

  const handlePatientFilter = (event) => {
    setFilterOptions({value: event.currentTarget.value});
  }

  const addNewSurvey = () => {
    SessionController.query("/api/addNewSurvey", {
      name: newSurveyDialog.surveyName
    }).then((response) => {
      if (response.status == 200) {
        console.log(response)
      }
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  useEffect(() => {
    const filterTimer = setTimeout(() => {
      
    }, 200);
    return () => clearTimeout(filterTimer);
  }, [filterOptions, surveys]);

  const currentDate = new Date();

  return (
    <DatabaseLayout>
      <MDBox>
        <Card sx={{marginTop: 5}}>
          <MDBox p={2}>
            <Grid container spacing={2}>
              <Grid item sm={12} md={6}>
                <MDTypography variant="h3">
                  {dictionary.Surveys.SurveyList[language]}
                </MDTypography>
              </Grid>
              <Grid item sm={12} md={6} display="flex" sx={{
                justifyContent: {
                  sm: "space-between",
                  md: "end"
                }
              }}>
                <MDInput label={dictionary.Surveys.SearchSurvey[language]} value={filterOptions.text} onChange={(value) => handlePatientFilter(value)} sx={{paddingRight: 2}}/>
                <MDButton variant="contained" color="info" onClick={() => setNewSurveyDialog({surveyName: "", state: true})}>
                  {dictionary.Surveys.AddNewSurvey[language]} 
                </MDButton>
              </Grid>
              <Grid item xs={12} sx={{marginTop: 2}}>
                <SurveyTable data={surveys} />
              </Grid>
            </Grid>
          </MDBox>
        </Card>
      </MDBox>

      {alert}
      
      <Dialog open={newSurveyDialog.state} onClose={() => setNewSurveyDialog({surveyName: "", state: false})}>
        <MDBox px={2} pt={2}>
          <MDTypography variant="h5">
            {dictionary.Surveys.AddNewSurvey[language]} 
          </MDTypography>
        </MDBox>
        <DialogContent>
          <TextField
            variant="standard"
            margin="dense" id="name"
            value={newSurveyDialog.surveyName}
            onChange={(event) => setNewSurveyDialog({...newSurveyDialog, surveyName: event.target.value})}
            label={dictionary.Surveys.AddNewSurvey[language]} type="text"
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <MDButton color="secondary" onClick={() => setNewSurveyDialog({surveyName: "", state: false})}>Cancel</MDButton>
          <MDButton color="info" onClick={() => addNewSurvey()}>Create</MDButton>
        </DialogActions>
      </Dialog>

    </DatabaseLayout>
  );
};

