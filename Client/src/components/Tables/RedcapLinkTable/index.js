import { useState, useEffect, memo } from "react"
import { useNavigate } from "react-router-dom";

import {
  Button,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  IconButton,
  Tooltip,
} from "@mui/material"

import { SessionController } from "database/session-control.js";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

import MDTypography from 'components/MDTypography';
import MDButton from "components/MDButton";
import MDBox from "components/MDBox";
import TablePagination from "./TablePagination.js";

const RedcapLinkTable = ({data, onDelete}) => {
  const [controller, dispatch] = usePlatformContext();
  const { language } = controller;

  const navigate = useNavigate();

  const viewPerPage = 10;
  const [displayData, setDisplayData] = useState([]);
  const [paginationControl, setPagination] = useState({
    currentPage: 0,
    totalPages: 0
  });

  useEffect(() => {
    setPagination({currentPage: 0, totalPages: Math.ceil(data.length / viewPerPage)});
  }, [data]);

  useEffect(() => {
    setDisplayData(data.slice(paginationControl.currentPage * viewPerPage, paginationControl.currentPage * viewPerPage + viewPerPage));
  }, [paginationControl]);

  const enableNotification = (id, reportId, state) => {
    SessionController.query("/api/surveySchedulerStatus", {
      linkageId: id,
      reportId: reportId,
      enabledState: state
    }).then((response) => {
      for (let schedule of data) {
        if (schedule.reportId == reportId) {
          schedule.twilioLink.enabled = state;
        }
      }
      setDisplayData(data.slice(paginationControl.currentPage * viewPerPage, paginationControl.currentPage * viewPerPage + viewPerPage));
    }).catch((error) => {

    });
  };

  const deleteNotification = (id, reportId) => {
    SessionController.query("/api/surveySchedulerSetup", {
      linkageId: id,
      removeSchedule: reportId
    }).then((response) => {
      data = data.filter((value) => {
        return value.reportId != reportId;
      });
      setDisplayData(data.slice(paginationControl.currentPage * viewPerPage, paginationControl.currentPage * viewPerPage + viewPerPage));
    }).catch((error) => {

    });
  };

  const capitalizeFirstLetter = (string) => {
    let newString = "";
    let words = string.split(" ");
    for (let i in words) {
      newString += words[i][0].toUpperCase() + words[i].slice(1);
      if (i < words.length-1) newString += " "
    }
    return newString;
  }

  return (
    <MDBox style={{overflowX: "auto"}}>
      <Table size="small">
        <TableHead sx={{display: "table-header-group"}}>
          <TableRow>
            {["RedcapTableName", "TwilioInfo", "CurrentSchedule"].map((col) => {
              return (
                <TableCell key={col} variant="head" style={{width: "28%", minWidth: 200, verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
                  <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}} onClick={()=>console.log({col})}>
                    {dictionaryLookup(dictionary.Surveys, col, language)}
                  </MDTypography>
                </TableCell>
            )})}
            <TableCell key={"viewedit"} variant="head" style={{minWidth: "100px", verticalAlign: "bottom", paddingBottom: 0, paddingTop: 0}}>
              <MDTypography variant="span" fontSize={12} fontWeight={"bold"} style={{cursor: "pointer"}}>
                {" "}
              </MDTypography>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {displayData.map((schedule) => {
            return <TableRow key={schedule.reportId}>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                  {capitalizeFirstLetter(schedule.redcapSurveyName.replaceAll("_"," "))}
                </MDTypography>
                <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                  {"Link by Survey " + schedule.surveyId}
                </MDTypography>
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                  {"Record ID: " + schedule.twilioLink.receiver}
                </MDTypography>
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDTypography variant="h6" fontSize={12} style={{marginBottom: 0}}>
                  {"Repeat " + schedule.twilioLink.repeat}
                </MDTypography>
                {schedule.twilioLink.timestamps.map((timestamp) => {
                  if (schedule.twilioLink.repeat === "daily") {
                    return <MDTypography key={timestamp} variant="p" fontSize={12} style={{marginBottom: 0}}>
                      {new Date(timestamp*1000).toLocaleTimeString(language, {
                        hour: "numeric",
                        minute: "numeric"
                      })}
                      <br/>
                    </MDTypography>
                  } else if (schedule.twilioLink.repeat === "weekly") {
                    return <MDTypography key={timestamp} variant="p" fontSize={12} style={{marginBottom: 0}}>
                      {new Date(timestamp*1000).toLocaleString(language, {
                        weekday: "long",
                        hour: "numeric",
                        minute: "numeric"
                      })}
                      <br/>
                    </MDTypography>
                  }
                })}
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDBox style={{display: "flex", flexDirection: "row", justifyContent: "space-between", height: "100%"}}>
                  <Tooltip title={schedule.twilioLink.enabled ? "Disable Notification" : "Enable Notification"} placement="top">
                    <MDButton color="info" size="small" onClick={() => enableNotification(schedule.id, schedule.reportId, !schedule.twilioLink.enabled)} sx={{marginRight: 1}}>
                      <MDTypography variant="contained" color={"white"} fontSize={12} style={{marginBottom: 0}}>
                        {schedule.twilioLink.enabled ? "Disable" : "Enable"}
                      </MDTypography>
                    </MDButton>
                  </Tooltip>
                  <Tooltip title="Delete Notification" placement="top">
                    <MDButton color="light" size="small" onClick={() => deleteNotification(schedule.id, schedule.reportId)}>
                      <MDTypography variant="contained" fontSize={12} style={{marginBottom: 0}}>
                        DELETE
                      </MDTypography>
                    </MDButton>
                  </Tooltip>
                </MDBox>
              </TableCell>
            </TableRow>
          })}
        </TableBody>
      </Table>
      <TablePagination totalCount={data.length} totalPages={paginationControl.totalPages} currentPage={paginationControl.currentPage} setPagination={setPagination} />
    </MDBox>
  );
};

export default memo(RedcapLinkTable);