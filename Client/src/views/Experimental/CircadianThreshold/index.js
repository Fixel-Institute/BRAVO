import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  Autocomplete,
  Backdrop,
  ClickAwayListener,
  Card,
  Grid,
} from "@mui/material"

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import FormField from "components/MDInput/FormField";
import LoadingProgress from "components/LoadingProgress";

// core components
import CircadianRhythm from "./CircadianRhythm";

import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { formatStimulationChannel } from "database/helper-function";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary } from "assets/translation.js";

function CircadianThreshold() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  const [data, setData] = useState([]);

  const [circadianData, setCircadianData] = useState({});

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: true});
    } else {
      setAlert(<LoadingProgress/>);
      SessionController.query("/api/queryAdaptiveGroups", {
        id: patientID, 
      }).then((response) => {
        setData(response.data);
        setAlert(null);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  useEffect(() => {
    console.log(data)
  }, [data]);

  const extractCircadianRhythm = (therapy,side) => {
    setAlert(<LoadingProgress/>);
    const channels = formatStimulationChannel(therapy[side].Channel);
    
    SessionController.query("/api/queryCircadianPower", {
      id: patientID, 
      therapyInfo: {
        Frequency: therapy[side].Frequency,
        FrequencyInHertz: therapy[side].SensingSetup.FrequencyInHertz,
        Hemisphere: side,
        Channel: channels.filter((channel) => channel.startsWith("E1")).length > 0 ? 1 : 2
      },
      timezoneOffset: new Date().getTimezoneOffset()*60
    }).then((response) => {
      setCircadianData(response.data)
      setAlert(
        <Backdrop
          sx={{ color: '#FFFFFF', zIndex: (theme) => theme.zIndex.drawer + 1 }}
          open={true}
          onClick={() => setAlert(null)}
        >
          {response.data.Power.length > 0 ? (
            <Card style={{padding: 15}}>
              <CircadianRhythm dataToRender={response.data} height={600} figureTitle={"CircadianRhythm"}/>
            </Card>
          ) : (
            <Card style={{padding: 50}}>
              <MDTypography variant={"h6"} fontSize={24}>
                {"No Available Data"}
              </MDTypography>
            </Card>
          )}
        </Backdrop>
      );
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

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
                      <MDBox p={2}>
                        <MDTypography variant={"h6"} fontSize={24}>
                          {"Left Hemisphere"} {dictionary.CircadianThreshold.AdaptiveGroups[language]} 
                        </MDTypography>
                      </MDBox>
                    </Grid>
                    {data.map((group) => {
                      if (!group.Therapy.LeftHemisphere) return;

                      return <Grid key={group.TherapyGroup} item xs={12} lg={6} sx={{paddingX: 2, paddingY: 2}}>
                        <Card sx={{paddingX: 2, paddingY: 3, cursor: "pointer", boxShadow: "0 4px 8px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19)"}}
                          onClick={() => group.Therapy["LeftHemisphere"].Mode === "BrainSense" ? extractCircadianRhythm(group.Therapy, "LeftHemisphere") : {}}
                        >
                          <MDBox style={{paddingY: 3}}>
                            <MDTypography variant={"h5"}>
                              {group.TherapyGroup} 
                            </MDTypography>
                            {group.Therapy["LeftHemisphere"].Mode === "BrainSense" ? (
                              <MDBox>
                                <MDTypography variant={"h6"} color={"info"}>
                                  {formatStimulationChannel(group.Therapy["LeftHemisphere"].Channel)} {" "}
                                  {group.Therapy["LeftHemisphere"].Frequency} {dictionary.FigureStandardUnit.Hertz[language]} {" "}
                                  {group.Therapy["LeftHemisphere"].PulseWidth} {dictionary.FigureStandardUnit.uS[language]}
                                </MDTypography>
                                <MDTypography variant={"h6"} color={"info"}>
                                  {"BrainSense Frequency: "}
                                  {group.Therapy["LeftHemisphere"].SensingSetup.FrequencyInHertz} {dictionary.FigureStandardUnit.Hertz[language]}
                                </MDTypography>
                                <MDTypography variant={"h6"} color={"info"}>
                                  {"Upper Threshold: "}
                                  {group.Therapy["LeftHemisphere"].LFPThresholds[1]} {dictionary.FigureStandardUnit.AU[language]}
                                  {` (${group.Therapy["LeftHemisphere"].CaptureAmplitudes[0]} ${dictionary.FigureStandardUnit.mA[language]})`}
                                </MDTypography>
                                <MDTypography variant={"h6"} color={"info"}>
                                  {"Lower Threshold: "}
                                  {group.Therapy["LeftHemisphere"].LFPThresholds[0]} {dictionary.FigureStandardUnit.AU[language]}
                                  {` (${group.Therapy["LeftHemisphere"].CaptureAmplitudes[1]} ${dictionary.FigureStandardUnit.mA[language]})`}
                                </MDTypography>
                              </MDBox>
                            ) : (
                              <MDTypography variant={"h6"} color={"error"}>
                                {"BrainSense Disabled"}
                              </MDTypography>
                            )}
                          </MDBox>
                        </Card>
                      </Grid>
                    })}
                  </Grid>
                </Card>
              </Grid>
              <Grid item xs={12}>
                <Card sx={{width: "100%"}}>
                  <Grid container>
                    <Grid item xs={12}>
                      <MDBox p={2}>
                        <MDTypography variant={"h6"} fontSize={24}>
                          {"Right Hemisphere"} {dictionary.CircadianThreshold.AdaptiveGroups[language]}
                        </MDTypography>
                      </MDBox>
                    </Grid>
                    {data.map((group) => {
                      if (!group.Therapy.RightHemisphere) return;

                      return <Grid key={group.TherapyGroup} item xs={12} lg={6} sx={{paddingX: 2, paddingY: 2}}>
                        <Card sx={{paddingX: 2, paddingY: 3, cursor: "pointer", boxShadow: "0 4px 8px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19)"}}
                          onClick={() => group.Therapy["RightHemisphere"].Mode === "BrainSense" ? extractCircadianRhythm(group.Therapy, "RightHemisphere") : {}}
                        >
                          <MDBox style={{paddingY: 3}}>
                            <MDTypography variant={"h5"}>
                              {group.TherapyGroup}
                            </MDTypography>
                            {group.Therapy["RightHemisphere"].Mode === "BrainSense" ? (
                              <MDBox>
                                <MDTypography variant={"h6"} color={"info"}>
                                  {formatStimulationChannel(group.Therapy["RightHemisphere"].Channel)} {" "}
                                  {group.Therapy["RightHemisphere"].Frequency} {dictionary.FigureStandardUnit.Hertz[language]} {" "}
                                  {group.Therapy["RightHemisphere"].PulseWidth} {dictionary.FigureStandardUnit.uS[language]}
                                </MDTypography>
                                <MDTypography variant={"h6"} color={"info"}>
                                  {"BrainSense Frequency: "}
                                  {group.Therapy["RightHemisphere"].SensingSetup.FrequencyInHertz} {dictionary.FigureStandardUnit.Hertz[language]}
                                </MDTypography>
                                <MDTypography variant={"h6"} color={"info"}>
                                  {"Upper Threshold: "}
                                  {group.Therapy["RightHemisphere"].LFPThresholds[1]} {dictionary.FigureStandardUnit.AU[language]}
                                  {` (${group.Therapy["RightHemisphere"].CaptureAmplitudes[0]} ${dictionary.FigureStandardUnit.mA[language]})`}
                                </MDTypography>
                                <MDTypography variant={"h6"} color={"info"}>
                                  {"Lower Threshold: "}
                                  {group.Therapy["RightHemisphere"].LFPThresholds[0]} {dictionary.FigureStandardUnit.AU[language]}
                                  {` (${group.Therapy["RightHemisphere"].CaptureAmplitudes[1]} ${dictionary.FigureStandardUnit.mA[language]})`}
                                </MDTypography>
                              </MDBox>
                            ) : (
                              <MDTypography variant={"h6"} color={"error"}>
                                {"BrainSense Disabled"}
                              </MDTypography>
                            )}
                          </MDBox>
                        </Card>
                      </Grid>
                    })}
                  </Grid>
                </Card>
              </Grid>
            </Grid>
          </MDBox>
        </MDBox>
      </DatabaseLayout>
    </>
  );
}

export default CircadianThreshold;
