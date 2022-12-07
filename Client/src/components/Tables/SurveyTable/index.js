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
import SurveyTablePagination from "./SurveyTablePagination.js";

const SurveyTable = ({data, onDelete}) => {
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
    setPagination({currentPage: 0, totalPages: Math.ceil(data.length / viewPerPage)})
  }, [data]);

  useEffect(() => {
    setDisplayData(data.slice(paginationControl.currentPage * viewPerPage, paginationControl.currentPage * viewPerPage + viewPerPage));
  }, [paginationControl]);

  const viewSurvey = (id) => {
    //navigate(`/survey/${id}`, {params: {}, replace: false});
    window.open(`/survey/${id}`,'_blank');
  };

  const editSurvey = (id) => {
    navigate(`/survey/${id}/edit`, {params: {}, replace: false});
  };

  const deleteSurvey = (id) => {
    onDelete(id);
  };

  return (
    <MDBox style={{overflowX: "auto"}}>
      <Table size="small">
        <TableHead sx={{display: "table-header-group"}}>
          <TableRow>
            {["SurveyTableName", "SurveyTableURL", "SurveyTableDate"].map((col) => {
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
          {displayData.map((survey) => {
            return <TableRow key={survey.id}>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDTypography variant="h6" fontSize={15} style={{marginBottom: 0}}>
                  {survey.name}
                </MDTypography>
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                  {survey.url}
                </MDTypography>
              </TableCell>
              <TableCell style={{borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <MDTypography variant="p" fontSize={12} style={{marginBottom: 0}}>
                  {new Date(survey.date * 1000).toLocaleString(language, SessionController.getDateTimeOptions("DateFull"))}
                </MDTypography>
              </TableCell>
              <TableCell style={{flex: true, flexDirection: "row", justifyContent: "space-between", borderBottom: "1px solid rgba(224, 224, 224, 0.4)"}}>
                <Tooltip title="View Survey" placement="top">
                  <IconButton color="info" size="small" onClick={() => viewSurvey(survey.url)} sx={{paddingX: 1}}>
                    <i className="fa-solid fa-eye"></i>
                  </IconButton>
                </Tooltip>
                <Tooltip title="Edit Survey" placement="top">
                  <IconButton color="secondary" size="small" onClick={() => editSurvey(survey.url)} sx={{paddingX: 1}}>
                    <i className="fa-solid fa-pen"></i>
                  </IconButton>
                </Tooltip>
                <Tooltip title="Delete Survey" placement="top">
                  <IconButton color="error" size="small" onClick={() => deleteSurvey(survey.url)} sx={{paddingX: 1}}>
                    <i className="fa-solid fa-xmark"></i>
                  </IconButton>
                </Tooltip>
              </TableCell>
            </TableRow>
          })}
        </TableBody>
      </Table>
      <SurveyTablePagination totalCount={data.length} totalPages={paginationControl.totalPages} currentPage={paginationControl.currentPage} setPagination={setPagination} />
    </MDBox>
  );
};

export default memo(SurveyTable);