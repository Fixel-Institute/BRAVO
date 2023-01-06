import React from "react";
import { useNavigate } from "react-router-dom";

import {
  Autocomplete,
  Card,
  Grid,
  Slider
} from "@mui/material"

// core components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";
import LoadingProgress from "components/LoadingProgress";

import DatabaseLayout from "layouts/DatabaseLayout";

import BrainSenseStreamingTable from "components/Tables/StreamingTable/BrainSenseStreamingTable";
import StimulationPSD from "./StimulationPSD";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

function MultipleSegmentAnalysis() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;
  const [recordingId, setRecordingId] = React.useState([]);

  const [data, setData] = React.useState([]);
  const [dataToRender, setDataToRender] = React.useState(false);
  const [figureGroups, setFigureGroups] = React.useState([]);
  const [channelInfos, setChannelInfos] = React.useState([]);
  const [leftHemispherePSD, setLeftHemispherePSD] = React.useState(false);
  const [rightHemispherePSD, setRightHemispherePSD] = React.useState(false);
  const [leftHemisphereBox, setLeftHemisphereBox] = React.useState(false);
  const [rightHemisphereBox, setRightHemisphereBox] = React.useState(false);

  const [centerFrequencyLeft, setCenterFrequencyLeft] = React.useState(0);
  const [centerFrequencyRight, setCenterFrequencyRight] = React.useState(0);
  
  const [timeFrequencyPlotHeight, setTimeFrequencyPlotHeight] = React.useState(600)
  const [alert, setAlert] = React.useState(null);

  React.useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      SessionController.query("/api/queryBrainSenseStreaming", {
        id: patientID,
        requestOverview: true,
      }).then((response) => {
        setData(response.data);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  const getRecordingData = (list) => {
    setAlert(<LoadingProgress/>);
    SessionController.query("/api/queryMultipleSegmentComparison", {
      id: patientID, 
      recordingIds: list
    }).then((response) => {
      setDataToRender(response.data);
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  // Divide all PSDs by day or by channel
  React.useEffect(() => {
    setFigureGroups(Object.keys(dataToRender));
  }, [dataToRender]);

  return (
    <>
      {alert}
      <DatabaseLayout>
        <MDBox pt={3}>
          <MDBox>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Card sx={{width: "100%"}}>
                  <Grid container>
                    <Grid item xs={12}>
                      <MDBox p={2} lineHeight={1}>
                        {data.length > 0 ? (
                          <BrainSenseStreamingTable data={data} toggle getRecordingData={getRecordingData}/>
                        ) : (
                          <MDTypography variant="h6" fontSize={24}>
                            {dictionary.WarningMessage.NoData[language]}
                          </MDTypography>
                        )}
                      </MDBox>
                    </Grid>
                  </Grid>
                </Card>
              </Grid>
              {figureGroups.map((title) => {
                let hemisphere = "Right";
                if (title.endsWith("LEFT")) {
                  hemisphere = "Left";
                }
                const channelInfos = dataToRender[title].map((result) => {
                  for (let i in data) {
                    if (data[i].RecordingID == result.RecordingID) {
                      for (let j in data[i].Channels) {
                        if (data[i].Channels[j].Hemisphere.startsWith(hemisphere)) return {Channel: data[i].Channels[j], Segment: data[i].ContactType[j]};
                      }
                    }
                  }
                });

                return <Grid key={title} item xs={12}>
                  <Card sx={{width: "100%"}}>
                    <Grid container>
                      <Grid item xs={12}>
                        <MDBox p={2} lineHeight={1}>
                          <StimulationPSD dataToRender={dataToRender[title]} channelInfos={channelInfos} figureTitle={title} height={600}/>
                        </MDBox>
                      </Grid>
                    </Grid>
                  </Card>
                </Grid>
              })}
            </Grid>
          </MDBox>
        </MDBox>
      </DatabaseLayout>
    </>
  );
}

export default MultipleSegmentAnalysis;
