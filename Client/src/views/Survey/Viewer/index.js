/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState, useRef } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import Papa from "papaparse";

import {
  Card,
  Checkbox,
  Grid,
  FormControl,
  FormControlLabel,
  InputLabel,
  Select,
  TextField,
  Stack,
  Slider,
  RadioGroup,
  Radio
} from "@mui/material";

import { 
  Remove as RemoveIcon,
  Add as AddIcon
} from "@mui/icons-material";

import MuiAlertDialog from "components/MuiAlertDialog";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";
import SurveyTable from "components/Tables/SurveyTable";
import LoadingProgress from "components/LoadingProgress";

import SurveyLayout from "layouts/SurveyLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

export default function SurveyViewer({match}) {
  const [controller, dispatch] = usePlatformContext();
  const { user, language } = controller;

  const [contents, setContents] = useState({contents: []});
  const [alert, setAlert] = useState(null);

  const [completed, setCompleted] = useState(false);

  const inputFile = useRef(null) 

  const { surveyId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    setAlert(<LoadingProgress/>);
    if (SessionController.getServer() === "") {
      SessionController.setServer("https://bravo-server.jcagle.solutions");
    }

    SessionController.query("/api/querySurveyContent", {
      id: surveyId
    }).then((response) => {
      if (response.status == 200) {
        setContents(response.data);
        setAlert(null);
      }
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }, []);

  const setTextQuestionValue = (index, questionId, value) => {
    contents.contents[index].questions[questionId].value = value;
    contents.contents[index].questions[questionId].changed = true;
    setContents({...contents});
  };

  const setScoreQuestionValue = (index, questionId, type, value) => {
    contents.contents[index].questions[questionId][type] = parseFloat(value);
    contents.contents[index].questions[questionId].changed = true;
    setContents({...contents});
  };

  const setMultipleChoiceValue = (index, questionId, type, value) => {
    contents.contents[index].questions[questionId][type] = value;
    contents.contents[index].questions[questionId].changed = true;
    setContents({...contents});
  };

  const submitSurvey = () => {
    let results = [];

    for (let index in contents.contents) {
      results.push([]);
      for (let questionId in contents.contents[index].questions) {
        if (contents.contents[index].questions[questionId].show && !contents.contents[index].questions[questionId].changed) {
          setAlert(
            <MuiAlertDialog title={"Incomplete Survey"} message={"You have not answered all questions"}
              handleClose={() => setAlert()} 
              handleConfirm={() => setAlert()}/>)
          return;
        }
        results[index].push(contents.contents[index].questions[questionId].value);
      }
    }

    SessionController.query("/api/submitSurvey", {
      id: surveyId,
      passcode: searchParams.get("__passcode"),
      version: contents.version,
      date: new Date().getTime(),
      results: results
    }).then((response) => {
      setCompleted(true);
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }

  return !completed ? (
    <SurveyLayout viewOnly>
      <MDBox>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Card sx={{marginTop: 0}}>
              <MDBox p={2}>
                <Grid container spacing={2}>
                  <Grid item xs={12} >
                    <MDBox sx={{display: "flex", flexDirection: "row", justifyContent: "flex-start", alignItem: "center"}}>
                      <MDTypography variant="h3">
                        {contents.title ? contents.title : ""}
                      </MDTypography>
                    </MDBox>
                  </Grid>
                  {contents.contents.map((page, index) => {
                    return <Grid key={index} item xs={12}>
                      <MDTypography variant="h3">
                        {page.header}
                      </MDTypography>
                      {page.questions.map((question, questionId) => {
                        if (!question.show) return null;

                        return <Grid key={questionId} container pt={1} spacing={2} mb={3}>
                          <Grid item xs={12} md={5} >
                            <MDTypography variant="h6">
                              {question.text}
                            </MDTypography>
                          </Grid>
                          <Grid item xs={12} md={7} >
                            {question.type == "score" ? (
                              <MDBox>
                                <Stack spacing={2} direction="row" alignItems={"center"} sx={{width: "100%"}}>
                                  <MDTypography variant="h3">
                                    {question.min}
                                  </MDTypography>
                                  <Slider aria-label="Default Value" valueLabelDisplay={"auto"}
                                    value={question.value} min={question.min} max={question.max} step={question.step} 
                                    onChange={(event) => setScoreQuestionValue(index, questionId, "value", event.target.value)} />
                                  <MDTypography variant="h3">
                                    {question.max}
                                  </MDTypography>
                                </Stack>
                                {question.changed ? null : (
                                  <MDTypography variant="h5" fontSize={12} color={"error"}>
                                    {"*Required"}
                                  </MDTypography>
                                )}
                              </MDBox>
                            ) : null}
                            {question.type == "text" ? (
                              <MDBox sx={{display: "flex", flexDirection: "column", justifyContent: "flex-start", alignItems: "center", marginY: 1}}>
                                <TextField variant={"standard"} value={question.value} label={"Default Text Field"} onChange={(event) => setTextQuestionValue(index, questionId, event.target.value)} rows={4} sx={{marginX: 1}} fullWidth multiline>
                                </TextField>
                                {question.changed ? null : (
                                  <MDTypography variant="h5" fontSize={12} color={"error"}>
                                    {"*Required"}
                                  </MDTypography>
                                )}
                              </MDBox>
                            ) : null}
                            {question.type == "multiple-choice" ? (
                              <MDBox displ>
                                {question.multiple ? (
                                  <Grid container spacing={0}>
                                    {question.options.map((option, optionId) => {
                                      let answerLength = 0;
                                      question.options.map((option) => {
                                        if (option.length > answerLength) answerLength = option.length;
                                      });

                                      return <Grid key={optionId} item xs={12} md={answerLength > 14 ? 12 : 12/question.options.length}>
                                        <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"}>
                                          <Radio
                                            checked={question.value.includes(option)}
                                            value={option}
                                            onClick={(event) => {
                                              if (question.value.includes(option) && question.value.length > 1) {
                                                setMultipleChoiceValue(index, questionId, "value", question.value.filter((text) => text != option));
                                              } else if (!question.value.includes(option)) {
                                                setMultipleChoiceValue(index, questionId, "value", [...question.value, option]);
                                              }
                                            }}
                                          />
                                          <MDTypography variant="h6" fontSize={13}>
                                            {option}
                                          </MDTypography>
                                        </MDBox>
                                      </Grid>
                                    })}
                                  </Grid>
                                ) : (
                                  <Grid container spacing={0}>
                                    {question.options.map((option) => {
                                      let answerLength = 0;
                                      question.options.map((option) => {
                                        if (option.length > answerLength) answerLength = option.length;
                                      });

                                      return <Grid item xs={12} md={answerLength > 14 ? 12 : 12/question.options.length}>
                                        <MDBox display={"flex"} flexDirection={"row"} alignItems={"center"}>
                                          <Radio
                                            checked={question.value == option}
                                            value={option}
                                            onClick={(event) => setMultipleChoiceValue(index, questionId, "value", option)}
                                          />
                                          <MDTypography variant="h6" fontSize={13}>
                                            {option}
                                          </MDTypography>
                                        </MDBox>
                                      </Grid>
                                    })}
                                  </Grid>
                                )}
                                {question.changed ? null : (
                                  <MDTypography variant="h5" fontSize={12} color={"error"}>
                                    {"*Required"}
                                  </MDTypography>
                                )}
                                {!question.multiple ? null : (
                                  <MDTypography variant="h5" fontSize={12} color={"error"}>
                                    {"*Multiple Allowed"}
                                  </MDTypography>
                                )}
                              </MDBox>
                            ) : null}
                          </Grid>
                        </Grid>
                      })}
                    </Grid>
                  })}
                </Grid>
              </MDBox>
            </Card>
          </Grid>
          <Grid item xs={12}>
            <MDBox p={2} style={{display: "flex", justifyContent: "center"}}>
              <MDButton variant={"contained"} color={"info"} onClick={submitSurvey} >
                <MDTypography variant="h6" color={"white"}>
                  {"Submit"}
                </MDTypography>
              </MDButton>
            </MDBox>
          </Grid>
        </Grid>
      </MDBox>
      {alert}
    </SurveyLayout>
  ) : (
    <SurveyLayout viewOnly>
      <MDBox>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Card sx={{marginTop: 0}}>
              <MDBox p={2}>
                {"Thank you for submitting the survey! You can close this window now."}
              </MDBox>
            </Card>
          </Grid>
        </Grid>
      </MDBox>
    </SurveyLayout>
  );
};

