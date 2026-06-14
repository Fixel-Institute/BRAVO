/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  Autocomplete,
  Drawer,
  Divider,
  ToggleButton,
  ToggleButtonGroup,
  Card,
  Grid,
  IconButton,
  SpeedDial,
  SpeedDialAction,
  SpeedDialIcon,
  Slider
} from "@mui/material"

import { 
  ChevronRight as ChevronRightIcon,
  Settings as SettingsIcon,
  KeyboardDoubleArrowUp as KeyboardDoubleArrowUpIcon, 
  Dashboard as DashboardIcon,
  Cached as CachedIcon
} from "@mui/icons-material";

// core components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";
import LoadingProgress from "components/LoadingProgress";
import MuiAlertDialog from "components/MuiAlertDialog";
import FormField from "components/MDInput/FormField";

import DatabaseLayout from "layouts/DatabaseLayout";
import ConfigurationDialog from "components/ConfigurationDialog";
import SnapshotPSDs from "./SnapshotPSDs";
import ChronicSnapshots from "./ChronicSnapshots";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

function NeuralActivitySnapshot() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { TherapeuticEffectLayout, language } = controller;
  const { participant_uid } = useParams();

  const [availableSnapshots, setAvailableSnapshots] = useState({Analyses: [], Recordings: []});
  const [viewSnapshot, setViewSnapshot] = useState("");
  const [viewChronicChannel, setViewChronicChannel] = useState({active: "", options: []});

  const [snapshot, setSnapshot] = useState([]);
  const [chronicSnapshot, setChronicSnapshot] = useState([]);

  const [monopolarEstimate, setMonopolarEstimate] = useState(false);

  const [drawerOpen, setDrawerOpen] = useState({open: false, config: {}});
  const [channel, setChannel] = useState({active: "", options: []});

  const [alert, setAlert] = useState(null);

  const getRecordingType = (type) => {
    if (type === "MedtronicBaselineMontages") {
      return "BrainSense Setup";
    } else if (type === "MedtronicBrainSenseSurvey") {
      return "BrainSense Survey";
    } else if (type === "MedtronicElectrodeIdentifier") {
      return "Electrode Identifier";
    } else {
      return type;
    }
  }

  useEffect(() => {
    if (!participant_uid) {
      navigate("/database", {replace: false});
      return;
    }
    setContextState(dispatch, "report", "GeneralReports");

    setAlert(<LoadingProgress/>);
    SessionController.query("/api/queryNeuralActivitySnapshot", {
      RequestType: "RequestAll",
      ParticipantId: participant_uid
    }).then((response) => {
      setViewChronicChannel(() => {
        let allChannels = response.data.Recordings.reduce((accumulator, a) => {
          for (let k in a.Channels) {
            if (!accumulator.includes(a.Channels[k])) {
              accumulator.push(a.Channels[k]);
            }
          }
          return accumulator
        }, []).sort((a,b) => a.localeCompare(b));
        allChannels = allChannels.map((a) => a.split(": ")[1]);

        if (allChannels.length > 0) return {active: allChannels[0], options: allChannels}
        return {active: "", options: []}
      });

      setAvailableSnapshots((data) => {
        let uniqueDates = [];
        for (let i in response.data.Recordings) {
          const dateString = new Date(response.data.Recordings[i].Date*1000).toLocaleString("en-US", {...SessionController.getTimezoneName(response.data.Recordings[i].Timezone),
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
          });
          response.data.Recordings[i].DateString = dateString;
          if (!uniqueDates.map((a) => a.dateString).includes(dateString)) uniqueDates.push({value: response.data.Recordings[i].Date, dateString});
        }
        uniqueDates = uniqueDates.sort((a,b) => b.value-a.value).map((a) => a.dateString);

        const findCommonItem = (arr1, arr2) => {
          const result = [];
          for (const el1 of arr1) {
            if (arr2.includes(el1)) {
              result.push(el1);
            }
          }
          return result;
        }

        let analyses = [];
        for (let i in uniqueDates) {
          const recordings = response.data.Recordings.filter((a) => a.DateString == uniqueDates[i]);
          let analysis = {
            Date: uniqueDates[i],
            RecordingIds: recordings.map((a) => a.Id),
            Channels: recordings.map((a) => a.Channels),
            Overview: []
          };
          
          for (let j in analysis.Channels) {
            for (let k in analysis.Channels[j]) {
              const target = analysis.Channels[j][k].split(" E")[0];
              if (!analysis.Overview.includes(target.split(": ")[1])) analysis.Overview.push(target.split(": ")[1]);
            }
          }
          analysis.Type = recordings[0].Type;
          analysis.Overview = analysis.Overview.join(" ")
          analyses.push(analysis);
        }

        if (analyses.length > 0) setViewSnapshot(analyses[0].Date + " | " + " (" + getRecordingType(analyses[0].Type) + ") " + analyses[0].Overview);
        return {Analyses: analyses, Recordings: response.data.Recordings};
      });
      setAlert(null);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
    
  }, [participant_uid]);

  useEffect(() => {
    setSnapshot(() => {
      for (let i in availableSnapshots.Analyses) {
        if (availableSnapshots.Analyses[i].Date + " | " + " (" + getRecordingType(availableSnapshots.Analyses[i].Type) + ") " +  availableSnapshots.Analyses[i].Overview == viewSnapshot) {
          let dataToRender = [];
          const overview = availableSnapshots.Analyses[i].Overview.split(" ");
          for (let j in availableSnapshots.Recordings) {
            if (availableSnapshots.Analyses[i].RecordingIds.includes(availableSnapshots.Recordings[j].Id)) {
              for (let k in availableSnapshots.Recordings[j].Channels) {
                dataToRender.push({
                  ChannelName: availableSnapshots.Recordings[j].Channels[k].split(" ").filter((a) => a).join(" "),
                  Frequency: availableSnapshots.Recordings[j].PSDs[k].Frequency,
                  Power: availableSnapshots.Recordings[j].PSDs[k].Power,
                  stdPower: availableSnapshots.Recordings[j].PSDs[k].stdPower.map((a) => a/Math.sqrt(availableSnapshots.Recordings[j].PSDs[k].nObservation))
                })
              }
            }
          }
          dataToRender.sort((a,b) => a.ChannelName.localeCompare(b.ChannelName))
          return dataToRender;
        }
      };
      return [];
    });
  }, [availableSnapshots, viewSnapshot]);

  useEffect(( ) => {
    setChronicSnapshot(() => {
      let allRecordings = []
      for (let i in availableSnapshots.Recordings) {
        for (let k in availableSnapshots.Recordings[i].Channels) {
          if (availableSnapshots.Recordings[i].Channels[k].split(": ")[1] == viewChronicChannel.active) {
            const dateString = new Date(availableSnapshots.Recordings[i].Date*1000).toLocaleString("en-US", {...SessionController.getTimezoneName(availableSnapshots.Recordings[i].Timezone),
              year: "numeric",
              month: "2-digit",
              day: "2-digit"
            })
            allRecordings.push({
              Date: dateString,
              DateTimestamp: availableSnapshots.Recordings[i].Date,
              Power: availableSnapshots.Recordings[i].PSDs[k].Power,
              Frequency: availableSnapshots.Recordings[i].PSDs[k].Frequency,
            })
          }
        }
      }
      return allRecordings.sort((a,b) => a.DateTimestamp-b.DateTimestamp);
    })
  }, [availableSnapshots, viewChronicChannel]);

  return (
    <DatabaseLayout>
      {alert}
      <MDBox pt={3}>
        <MDBox>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <Card sx={{width: "100%"}}>
                {availableSnapshots.Analyses.length > 0 ? (
                <Grid container>
                  <Grid item xs={12}>
                    <MDBox pt={2} px={2} lineHeight={1} display={"flex"} flexDirection={"row"} justifyContent={"space-between"} alignItems={"center"}>
                      <MDTypography variant="h6" fontSize={24}>
                        {"Neural Activity PSDs"}
                      </MDTypography>
                      <MDButton color={"info"} style={{marginLeft: 10}} onClick={() => {
                        const url = SessionController.getDownloadLink("/api/downloadData", {
                          ParticipantId: participant_uid,
                          CacheType: "queryNeuralActivitySnapshot"
                        });
                        window.location.href=url;
                      }}>
                        {"Export All PSDs"}
                      </MDButton>
                    </MDBox>
                    <MDBox pb={2} px={2} lineHeight={1}>
                      <Autocomplete
                        value={viewSnapshot}
                        options={availableSnapshots.Analyses.map((a) => a.Date + " | " + " (" + getRecordingType(a.Type) + ") " + a.Overview)}
                        onChange={(event, value) => {
                          setViewSnapshot(value)
                        }}
                        renderInput={(params) => (
                          <FormField
                            {...params}
                            label={dictionary.TherapeuticAnalysis.Table.TableTitle[language]}
                            InputLabelProps={{ shrink: true }}
                          />
                        )}
                      />
                    </MDBox>
                  </Grid>
                  <Grid item xs={12}>
                    <MDBox position="relative">
                      <MDBox sx={{position: "absolute", top: 54, right: 8, zIndex: 2, pointerEvents: "auto"}}>
                        <ToggleButton
                          value={"monopolar"}
                          selected={monopolarEstimate}
                          onChange={() => setMonopolarEstimate((p) => !p)}
                          size="small"
                          sx={{fontSize: 12}}
                        >
                          {"Monopolar Estimate (Fleeting et. al. 2026)"}
                        </ToggleButton>
                      </MDBox>
                      <SnapshotPSDs dataToRender={snapshot} figureTitle={"Neural Activity Montages"} monopolarEstimate={monopolarEstimate} />
                    </MDBox>
                  </Grid>
                </Grid>
                ) : (
                  <MDBox p={2} lineHeight={1}>
                    <MDTypography variant="h6" fontSize={24}>
                      {dictionary.WarningMessage.NoData[language]}
                    </MDTypography>
                  </MDBox>
                )}
              </Card>
            </Grid>
            <Grid item xs={12}>
              <Card sx={{width: "100%"}}>
                {viewChronicChannel.options.length > 0 ? (
                <Grid container>
                  <Grid item xs={12}>
                    <MDBox p={2} lineHeight={1}>
                        <Autocomplete
                          value={viewChronicChannel.active}
                          options={viewChronicChannel.options}
                          onChange={(event, value) => setViewChronicChannel({...viewChronicChannel, active: value})}
                          renderInput={(params) => (
                            <FormField
                              {...params}
                              label={"Select Channel Name to View Snapshot Across Time"}
                              InputLabelProps={{ shrink: true }}
                            />
                          )}
                        />
                    </MDBox>
                  </Grid>
                  <Grid item xs={12}>
                    <ChronicSnapshots dataToRender={chronicSnapshot} figureTitle={"Snapshot across Time"} />
                  </Grid>
                </Grid>
                ) : (
                  <MDBox p={2} lineHeight={1}>
                    <MDTypography variant="h6" fontSize={24}>
                      {dictionary.WarningMessage.NoData[language]}
                    </MDTypography>
                  </MDBox>
                )}
              </Card>
            </Grid>
          </Grid>
          <ConfigurationDialog show={drawerOpen.open} setShow={(state) => setDrawerOpen({open: state})} setAlert={setAlert} />
          <MDBox style={{
            position: 'sticky',
            bottom: 32,
            right: 32,
            pointerEvents: "none"
          }}>
            <SpeedDial
              ariaLabel={"SurveySpeedDial"}
              color={"info"}
              icon={<SpeedDialIcon sx={{display: "flex", justifyContent: "center", alignItems: "center", fontSize: 30}}/>}
              FabProps={{
                color: "info",
                sx: {display: "flex", marginLeft: "auto"}
              }}
              sx={{alignItems: "end"}}
              hidden={false}
            >
              <SpeedDialAction
                key={"GoToTop"}
                icon={<KeyboardDoubleArrowUpIcon sx={{display: "flex", justifyContent: "center", alignItems: "center", fontSize: 30}}/>}
                tooltipTitle={"Go to Top"}
                onClick={() => {
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
              />
              <SpeedDialAction
                key={"ChangeSettings"}
                icon={<SettingsIcon sx={{display: "flex", justifyContent: "center", alignItems: "center", fontSize: 30}}/>}
                tooltipTitle={"Edit Processing Configurations"}
                onClick={() => setDrawerOpen({...drawerOpen, open: true})}
              />
              <SpeedDialAction
                key={"ClearCache"}
                icon={<CachedIcon sx={{display: "flex", justifyContent: "center", alignItems: "center", fontSize: 30}}/>}
                tooltipTitle={"Clear Cache (Reprocessing)"}
                onClick={() => {
                  SessionController.query("/api/queryNeuralActivitySnapshot", {
                    RequestType: "DeleteCache",
                    ParticipantId: participant_uid,
                  }).then((response) => {
                    window.location.reload();
                  });
                }}
              />
            </SpeedDial>
          </MDBox>
        </MDBox>
      </MDBox>
    </DatabaseLayout>
  );
}

export default NeuralActivitySnapshot;
