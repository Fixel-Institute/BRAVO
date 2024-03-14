/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  Autocomplete,
  Dialog,
  DialogContent,
  TextField,
  Card,
  Grid,
  IconButton,
  InputLabel,
  Input,
} from "@mui/material"

import { createFilterOptions } from "@mui/material/Autocomplete";

import OpenInBrowserIcon from '@mui/icons-material/OpenInBrowser';

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MuiAlertDialog from "components/MuiAlertDialog";
import LoadingProgress from "components/LoadingProgress";

// core components
import ResultViewer from "./ResultViewers";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary } from "assets/translation.js";
import MDButton from "components/MDButton";

const filter = createFilterOptions();

function AnalysisResultViewer({analysisId, analysisData}) {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  const [data, setData] = useState(false);
  const [dataToRender, setDataToRender] = useState({});
  const [availableResults, setAvailableResults] = useState([]);
  const [selectedRecording, setSelectedRecording] = useState(null);

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      setData(analysisData);
      setAvailableResults(analysisData.Configuration.Results.map((result) => {
        return {
          type: result.Type,
          key: result.ProcessedData,
          title: "[" + result.Type + "] " + result.ResultLabel,
          value: result.ProcessedData
        }
      }));
    }
  }, [patientID, analysisId, analysisData]);

  useEffect(() => {
  }, [selectedRecording]);

  const handleDownloadData = () => {
    if (selectedRecording) {
      setAlert(<LoadingProgress/>);
      SessionController.query("/api/queryCustomizedAnalysis", {
        id: patientID, 
        requestResult: analysisId,
        resultId: selectedRecording.value,
        download: true
      }, {}, null, "arraybuffer").then((response) => {
        setAlert(null);

        const url = window.URL.createObjectURL(
          new Blob([response.data]),
        );
        var downloader = document.createElement('a');
        downloader.href = url;
        downloader.target = '_blank';
        downloader.download = selectedRecording.title;
        downloader.click();
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }

  return data ? (
    <Card width={"100%"} style={{paddingTop: 15, paddingBottom: 15, paddingLeft: 15, paddingRight: 15}}>
      {alert}
      <MDBox>
        <MDTypography fontWeight={"bold"} fontSize={30}>
          {data.Analysis.AnalysisName} {" - Result Viewer"}
        </MDTypography>
        <MDTypography fontSize={18}>
          {"Last Modified: "}{new Date(data.Analysis.AnalysisDate*1000).toLocaleDateString()}
        </MDTypography>
      </MDBox>
      <MDBox pt={2}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            
          </Grid>
          <Grid item xs={12}>
            <Autocomplete 
              selectOnFocus 
              clearOnBlur
              renderInput={(params) => (
                <TextField
                  {...params}
                  variant="standard"
                  placeholder={"Select Recordings"}
                />
              )}
              filterOptions={(options, params) => {
                const filtered = filter(options, params);
                const { inputValue } = params;
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
              value={selectedRecording}
              options={availableResults}
              onChange={(event, newValue) => setSelectedRecording(newValue)}
              disableClearable
            />
          </Grid>
          <Grid item xs={12}>
            {selectedRecording ? (
            <MDButton color={"info"} 
              onClick={handleDownloadData} style={{marginLeft: 10}}
            >
              {selectedRecording.type === "AlignedData" ? "Download" : ""}
            </MDButton>
            ) : null}
            <ResultViewer data={dataToRender} />
          </Grid>
        </Grid>
      </MDBox>
    </Card>
  ) : null;
}

export default AnalysisResultViewer;
