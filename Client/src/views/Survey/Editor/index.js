import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import {
  Card,
  Checkbox,
  Grid,
  FormControl,
  FormControlLabel,
  InputLabel,
  Select,
  Stack,
  Slider,
  MenuItem,
  Dialog,
  DialogContent,
  DialogActions,
  TextField,
  IconButton,
  Button
} from "@mui/material";

import { 
  Remove as RemoveIcon,
  Add as AddIcon
} from "@mui/icons-material";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";
import SurveyTable from "components/Tables/SurveyTable";

import SurveyLayout from "layouts/SurveyLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

export default function SurveyEditor({match}) {
  const [controller, dispatch] = usePlatformContext();
  const { user, language } = controller;

  const [contents, setContents] = useState({contents: []});
  const [alert, setAlert] = useState(null);

  const [editText, setEditText] = useState(false);

  const { surveyId } = useParams();

  useEffect(() => {
    SessionController.query("/api/querySurveyContent", {
      id: surveyId
    }).then((response) => {
      if (response.status == 200) {
        if (!response.data.editable) {
          SessionController.displayError({response: {status: 403}}, setAlert);
        } else {
          setContents(response.data);
        }
      }
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }, []);

  useEffect(() => {
    const updateTimer = setTimeout(() => {
      SessionController.query("/api/updateSurveyContent", {
        id: surveyId,
        title: contents.title,
        contents: contents.contents
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
      console.log(contents.contents)
    }, 5000);
    return () => clearTimeout(updateTimer);
  }, [contents])

  const addPage = () => {
    contents.contents.push({
      header: "New Page",
      questions: []
    });
    setContents({...contents});
  };

  const addQuestion = (index) => {
    contents.contents[index].questions.push({
      type: "text",
      text: "Edit your question statement here",
      value: "",
      default: ""
    });
    setContents({...contents});
  };

  const setPageHeader = (index, text) => {
    contents.contents[index].header = text;
    setContents({...contents});
  };

  const setQuestionText = (index, questionId, text) => {
    contents.contents[index].questions[questionId].text = text;
    setContents({...contents});
  };

  const setQuestionType = (index, questionId, type) => {
    if (type === "score") {
      contents.contents[index].questions[questionId] = {
        text: contents.contents[index].questions[questionId].text,
        type: type,
        min: 0,
        max: 100,
        step: 1,
        value: 0,
        default: 0
      };
    } else if (type === "text") {
      contents.contents[index].questions[questionId] = {
        text: contents.contents[index].questions[questionId].text,
        type: type,
        value: "",
        default: ""
      };
    } else if (type === "multiple-choice") {
      contents.contents[index].questions[questionId] = {
        text: contents.contents[index].questions[questionId].text,
        type: type,
        multiple: false,
        value: [],
        options: [],
        default: [],
      };
    }
    setContents({...contents});
  };

  const setTextQuestionValue = (index, questionId, value) => {
    contents.contents[index].questions[questionId].value = value;
    contents.contents[index].questions[questionId].default = value;
    setContents({...contents});
  };

  const setScoreQuestionValue = (index, questionId, type, value) => {
    contents.contents[index].questions[questionId][type] = parseFloat(value);
    if (type === "value") contents.contents[index].questions[questionId].default = value;
    setContents({...contents});
  };

  const setChoiceQuestionValue = (index, questionId, type, value) => {
    contents.contents[index].questions[questionId][type] = value;
    setContents({...contents});
  };

  return (
    <SurveyLayout>
      <MDBox>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Card sx={{marginTop: 0}}>
              <MDBox p={2}>
                <Grid container spacing={2}>
                  <Grid item xs={12} >
                    <MDBox sx={{display: "flex", flexDirection: "row", justifyContent: "flex-start", alignItem: "center"}}>
                      {editText === "contentName" ? (
                        <TextField variant={"standard"} value={contents.title} onChange={(event) => setContents({...contents, title: event.target.value})} sx={{marginX: 1}}>
                        </TextField>
                      ) : (
                        <MDTypography variant="h3">
                          {contents.title ? contents.title : ""}
                        </MDTypography>
                      )}
                      <IconButton onClick={() => editText === "contentName" ? setEditText(false) : setEditText("contentName")}>
                        <i className="fa-solid fa-pen"></i>
                      </IconButton>
                    </MDBox>
                  </Grid>
                </Grid>
              </MDBox>
            </Card>
          </Grid>
          {contents.contents.map((page, index) => {
            return (
              <Grid item xs={12} key={index}>
                <Card sx={{marginY: 2}}>
                  <MDBox p={2}>
                    <Grid container spacing={2}>
                      <Grid item xs={12} sx={{marginBottom: 2}}>
                        <MDBox sx={{display: "flex", flexDirection: "row", justifyContent: "flex-start", alignItems: "center"}}>
                          {editText === `page${index}Header` ? (
                            <TextField variant={"standard"} value={page.header} onChange={(event) => setPageHeader(index, event.target.value)} sx={{marginX: 1}}>
                            </TextField>
                          ) : (
                            <MDTypography variant="h3">
                              {page.header}
                            </MDTypography>
                          )}
                          <IconButton onClick={() => editText === `page${index}Header` ? setEditText(false) : setEditText(`page${index}Header`)}>
                            <i className="fa-solid fa-pen"></i>
                          </IconButton>
                        </MDBox>
                      </Grid>
                      {page.questions.map((question, questionId) => {
                        return (
                          <Grid item xs={12} sx={{borderTop: "5px solid rgba(224, 224, 224, 0.4)"}} key={questionId}>
                            <MDBox sx={{display: "flex", flexDirection: "row", justifyContent: "flex-start", alignItems: "center", marginY: 1}}>
                              <MDTypography variant="h6" style={{marginRight: 3}}>
                                {"Question: "}
                              </MDTypography>
                              <TextField variant={"standard"} value={question.text} onChange={(event) => setQuestionText(index, questionId, event.target.value)} sx={{marginX: 1}} fullWidth>
                              </TextField>
                            </MDBox>
                            <MDBox sx={{display: "flex", flexDirection: "row", justifyContent: "flex-start", alignItems: "center", marginY: 1}}>
                              <MDTypography variant="h6" style={{marginRight: 3}}>
                                {"Type: "}
                              </MDTypography>
                              <FormControl variant="standard" sx={{ marginX: 1, minWidth: 120 }}>
                                <Select
                                  value={question.type}
                                  onChange={(event) => setQuestionType(index, questionId, event.target.value)}
                                >
                                  <MenuItem value={"score"}>{"Score"}</MenuItem>
                                  <MenuItem value={"text"}>{"Text"}</MenuItem>
                                  <MenuItem value={"multiple-choice"}>{"Multiple Choice"}</MenuItem>
                                </Select>
                              </FormControl>
                              {question.type === "multiple-choice" ? (
                                <FormControlLabel label={"Allow Multiple"}
                                  control={<Checkbox checked={question.multiple} onChange={(event) => setChoiceQuestionValue(index, questionId, "multiple", event.target.checked)}/>}
                                />
                              ) : null} 
                            </MDBox>
                            {question.type === "text" ? (
                            <MDBox sx={{display: "flex", flexDirection: "row", justifyContent: "flex-start", alignItems: "center", marginY: 1}}>
                              <TextField variant={"standard"} value={question.value} label={"Default Text Field"} onChange={(event) => setTextQuestionValue(index, questionId, event.target.value)} rows={4} sx={{marginX: 1}} fullWidth multiline>
                              </TextField>
                            </MDBox>
                            ) : null}
                            {question.type === "score" ? (
                            <MDBox sx={{display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", marginY: 1}}>
                              <MDBox sx={{display: "flex", flexDirection: "row", width: "100%", justifyContent: "space-between", alignItems: "center", marginY: 2}}>
                                <MDInput type="number" label="Min" value={question.min} onChange={(event) => setScoreQuestionValue(index, questionId, "min", event.target.value)} />
                                <MDInput type="number" label="Step" value={question.step} onChange={(event) => setScoreQuestionValue(index, questionId, "step", event.target.value)} />
                                <MDInput type="number" label="Max" value={question.max} onChange={(event) => setScoreQuestionValue(index, questionId, "max", event.target.value)} />
                              </MDBox>
                              <Stack spacing={2} direction="row" alignItems={"center"} sx={{width: "100%"}}>
                                <RemoveIcon />
                                  <Slider aria-label="Default Value" marks valueLabelDisplay={"auto"}
                                    value={question.value} min={question.min} max={question.max} step={question.step} 
                                    onChange={(event) => setScoreQuestionValue(index, questionId, "value", event.target.value)} />
                                <AddIcon />
                              </Stack>
                            </MDBox>
                            ) : null}
                            {question.type === "multiple-choice" ? (
                            <MDBox sx={{display: "flex", flexDirection: "column", justifyContent: "flex-start", marginY: 1}}>
                              <MDButton variant={"contained"} color={"warning"} onClick={() => setChoiceQuestionValue(index, questionId, "options", [...question.options, "New Choice"])}>
                                {"Add Option"}
                              </MDButton>
                              {question.options.map((option, letter) => {
                                return <MDBox style={{display: "flex", marginTop: 5}} key={letter}>
                                  {editText === `page${index}question${questionId}option${letter}` ? (
                                    <TextField variant={"standard"} value={option} onChange={(event) => {
                                      question.options[letter] = event.target.value;
                                      setChoiceQuestionValue(index, questionId, "options", [...question.options])
                                    }} sx={{marginX: 1}}>
                                    </TextField>
                                  ) : (
                                    <MDButton variant={"outlined"} color={"info"} fullWidth>
                                      <MDTypography variant="h3">
                                        {option}
                                      </MDTypography>
                                    </MDButton>
                                  )}
                                  <IconButton onClick={() => editText === `page${index}question${questionId}option${letter}` ? setEditText(false) : setEditText(`page${index}question${questionId}option${letter}`)}>
                                    <i className="fa-solid fa-pen"></i>
                                  </IconButton>
                                </MDBox>
                              })}
                            </MDBox>
                            ) : null}
                          </Grid>
                        );
                      })}
                      <Grid item xs={12}>
                        <MDBox p={2} style={{display: "flex", justifyContent: "center"}}>
                          <MDButton variant={"contained"} color={"info"} onClick={() => addQuestion(index)} >
                            <MDTypography variant="p" color={"white"}>
                              {"New Question"}
                            </MDTypography>
                          </MDButton>
                        </MDBox>
                      </Grid>
                    </Grid>
                  </MDBox>
                </Card>
              </Grid>
            );
          })}
          <Grid item xs={12}>
            <MDBox p={2} style={{display: "flex", justifyContent: "center"}}>
              <MDButton variant={"contained"} color={"info"} onClick={addPage} >
                <MDTypography variant="h6" color={"white"}>
                  {"New Page"}
                </MDTypography>
              </MDButton>
            </MDBox>
          </Grid>
        </Grid>
      </MDBox>
      {alert}
    </SurveyLayout>
  );
};

