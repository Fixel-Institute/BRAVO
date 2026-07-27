/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState, useRef } from "react";
import { useParams } from "react-router-dom";

import Papa from "papaparse";

import {
  Autocomplete,
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
  Input,
  Button
} from "@mui/material";

import { 
  Remove as RemoveIcon,
  Add as AddIcon
} from "@mui/icons-material";

import { FaPen, FaXmark } from "react-icons/fa6";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";
import SurveyTable from "components/Tables/SurveyTable";
import FormField from "components/MDInput/FormField";

import SurveyLayout from "layouts/SurveyLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context";
import { dictionary, dictionaryLookup } from "assets/translation";

export default function FormEditor({match}) {
  const [controller, dispatch] = usePlatformContext();
  const { user, language } = controller;

  const [contents, setContents] = useState({contents: []});
  const [alert, setAlert] = useState(null);

  const [editText, setEditText] = useState(false);
  const inputFile = useRef(null) 
  const { form_link } = useParams();

  useEffect(() => {
    SessionController.query("/api/querySurveyForms", {
      RequestType: "RequestForm",
      FormLink: form_link
    }).then((response) => {
      if (!response.data.Editable) {
        SessionController.displayError({response: {status: 403}}, setAlert);
      } else {
        setContents({
          ...response.data,
          contents: response.data.Record
        });
      }
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  }, []);

  const parseRedcapInstrument = (content) => {
    var data = Papa.parse(content, {
      header: true
    });

    contents.contents = [];
    contents.contents.push({
      header: "",
      questions: []
    });

    for (let i in data.data) {
      if (data.data[i]["Field Type"] === "descriptive") {
        contents.contents[0].questions.push({
          variableName: data.data[i]["Variable / Field Name"],
          type: "description",
          text: data.data[i]["Field Label"],
          value: "",
          default: "",
          show: data.data[i]["Field Note"] != "hide"
        });
      } else if (data.data[i]["Field Type"] === "checkbox") {
        let options = data.data[i]["Choices, Calculations, OR Slider Labels"].split("|");

        contents.contents[0].questions.push({
          variableName: data.data[i]["Variable / Field Name"],
          type: "multiple-choice",
          text: data.data[i]["Field Label"],
          multiple: true,
          value: [],
          options: options.map((text) => {
            let position = text.search(",");
            let textOption = text.slice(position+1);
            return textOption.trim();
          }),
          default: [],
          show: data.data[i]["Field Note"] != "hide"
        });
      } else if (data.data[i]["Field Type"] === "notes") {
        contents.contents[0].questions.push({
          variableName: data.data[i]["Variable / Field Name"],
          type: "text",
          text: data.data[i]["Field Label"],
          value: "",
          default: "",
          validation: "text",
          show: data.data[i]["Field Note"] != "hide"
        });
      } else if (data.data[i]["Field Type"] === "text") {
        contents.contents[0].questions.push({
          variableName: data.data[i]["Variable / Field Name"],
          type: "text",
          text: data.data[i]["Field Label"],
          value: "",
          default: "",
          validation: data.data[i]["Text Validation Type OR Show Slider Number"],
          show: data.data[i]["Field Note"] != "hide"
        });
      } else if (data.data[i]["Field Type"] === "radio") {
        let options = data.data[i]["Choices, Calculations, OR Slider Labels"].split("|");
        
        contents.contents[0].questions.push({
          variableName: data.data[i]["Variable / Field Name"],
          type: "multiple-choice",
          text: data.data[i]["Field Label"],
          multiple: false,
          value: [],
          options: options.map((text) => {
            let position = text.search(",");
            let textOption = text.slice(position+1);
            return textOption.trim();
          }),
          default: [],
          show: data.data[i]["Field Note"] != "hide"
        });
      } else if (data.data[i]["Field Type"] === "dropdown") {
        let options = data.data[i]["Choices, Calculations, OR Slider Labels"].split("|");
        
        contents.contents[0].questions.push({
          variableName: data.data[i]["Variable / Field Name"],
          type: "multiple-choice",
          text: data.data[i]["Field Label"],
          multiple: false,
          value: [],
          options: options.map((text) => {
            let position = text.search(",");
            let textOption = text.slice(position+1);
            return textOption.trim();
          }),
          default: [],
          show: data.data[i]["Field Note"] != "hide"
        });
      } else if (data.data[i]["Field Type"] === "slider") {
        let options = data.data[i]["Choices, Calculations, OR Slider Labels"].split("|");
        contents.contents[0].questions.push({
          variableName: data.data[i]["Variable / Field Name"],
          type: "score",
          text: data.data[i]["Field Label"],
          min: parseInt(options[0].trim()),
          max: parseInt(options[2].trim()),
          step: 1,
          value: parseInt(options[1].trim()),
          default: parseInt(options[1].trim()),
          show: data.data[i]["Field Note"] != "hide"
        });
      } 
    }

    setContents({...contents});
  };

  const saveChanges = () => {
    SessionController.query("/api/setSurveyForms", {
      RequestType: "Update",
      FormLink: form_link,
      FormContent: contents.contents
    }).then((response) => {
      
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const addPage = () => {
    contents.contents.push({
      header: "",
      questions: []
    });
    setContents({...contents});
  };

  const deletePage = (index) => {
    contents.contents = contents.contents.filter((content, i) => i != index);
    setContents({...contents});
  };

  const addQuestion = (index) => {
    contents.contents[index].questions.push({
      type: "text",
      text: "Edit your question statement here",
      value: "",
      default: "",
      validation: "text",
      show: true
    });
    setContents({...contents});
  };

  const deleteQuestion = (index, questionId) => {
    contents.contents[index].questions = contents.contents[index].questions.filter((question, id) => id != questionId)
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
        default: 0,
        activeView: false,
        show: true
      };
    } else if (type === "redcapForm") {
      contents.contents[index].questions[questionId] = {
        text: contents.contents[index].questions[questionId].text,
        type: type,
        value: "",
        default: "",
        validation: "variable",
        activeView: false,
        show: true
      };
    } else if (type === "text") {
      contents.contents[index].questions[questionId] = {
        text: contents.contents[index].questions[questionId].text,
        type: type,
        value: "",
        default: "",
        validation: "text",
        activeView: false,
        show: true
      };
    } else if (type === "multiple-choice") {
      contents.contents[index].questions[questionId] = {
        text: contents.contents[index].questions[questionId].text,
        type: type,
        multiple: false,
        value: [],
        options: [],
        default: [],
        activeView: false,
        show: true
      };
    } else if (type === "description") {
      contents.contents[index].questions[questionId] = {
        text: contents.contents[index].questions[questionId].text,
        type: type,
        value: "",
        default: "",
        activeView: false,
        show: true
      };
    } else if (type === "cumulativeScore") {
      contents.contents[index].questions[questionId] = {
        text: contents.contents[index].questions[questionId].text,
        type: type,
        list: [],
        activeView: false,
        show: false
      };
    }
    setContents({...contents});
  };

  const setQuestionDisplay = (index, questionId, value) => {
    contents.contents[index].questions[questionId]["show"] = value;
    setContents({...contents});
  };

  const setQuestionRequired = (index, questionId, value) => {
    contents.contents[index].questions[questionId]["changed"] = !value;
    setContents({...contents});
  };

  const setQuestionAlwaysView = (index, questionId, value) => {
    contents.contents[index].questions[questionId]["activeView"] = value;
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

  const deleteChoiceQuestionOption = (index, questionId, letter) => {
    contents.contents[index].questions[questionId].options = contents.contents[index].questions[questionId].options.filter((option, i) => letter != i);
    setContents({...contents});
  }

  const setCumulativeScoreInclusion = (index, questionId, value) => {
    if (value.includes("All Scores")) {
      contents.contents.map((a) => {
        a.questions.map((b) => {
          if (b.type == "score") {
            if (!contents.contents[index].questions[questionId].list.includes(b.text)) {
              contents.contents[index].questions[questionId].list.push(b.text);
            }
          }
        })
      })
    } else {
      contents.contents[index].questions[questionId].list = value;
    }
    setContents({...contents});
  }

  return (
    <SurveyLayout>
      <MDBox>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Card sx={{marginTop: 0}}>
              <MDBox p={2}>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6} >
                    <MDBox sx={{display: "flex", flexDirection: "row", justifyContent: "flex-start", alignItem: "center"}}>
                      <MDTypography variant="h3">
                        {contents.Name ? contents.Name : ""}
                      </MDTypography>
                    </MDBox>
                  </Grid>
                  <Grid item xs={12} sm={6} >
                    <MDBox sx={{display: "flex", flexDirection: "row", justifyContent: "flex-end", alignItem: "center"}}>
                      <MDButton variant={"contained"} color={"info"} onClick={() => inputFile.current.click()} sx={{marginRight: 3}}>
                        <MDTypography variant="p" color={"white"}>
                          {"Populate with Redcap Instrument"}
                        </MDTypography>
                      </MDButton>

                      <Input inputRef={inputFile} type={"file"} inputProps={{accept: ".csv"}} style={{display: "none"}} onChange={(event) => {
                        const reader = new FileReader();
                        reader.onload = () => parseRedcapInstrument(reader.result);
                        reader.readAsBinaryString(event.target.files[0]);
                      }} />

                      <MDButton variant={"contained"} color={"success"} onClick={() => saveChanges()}>
                        <MDTypography variant="p" color={"white"}>
                          {"Save Changes"}
                        </MDTypography>
                      </MDButton>
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
                            <FaPen />
                          </IconButton>
                          <IconButton color={"error"} onClick={() => deletePage(index)}>
                            <FaXmark />
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
                              <IconButton color={"error"} onClick={() => deleteQuestion(index, questionId)}>
                                <FaXmark />
                              </IconButton>
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
                                  <MenuItem value={"redcapForm"}>{"Redcap Variable"}</MenuItem>
                                  <MenuItem value={"score"}>{"Score"}</MenuItem>
                                  <MenuItem value={"text"}>{"Text"}</MenuItem>
                                  <MenuItem value={"multiple-choice"}>{"Multiple Choice"}</MenuItem>
                                  <MenuItem value={"description"}>{"Description"}</MenuItem>
                                  <MenuItem value={"cumulativeScore"}>{"Cumulative Score"}</MenuItem>
                                </Select>
                              </FormControl>
                              {question.type === "multiple-choice" ? (
                                <FormControlLabel label={"Allow Multiple"}
                                  control={<Checkbox checked={question.multiple} onChange={(event) => setChoiceQuestionValue(index, questionId, "multiple", event.target.checked)}/>}
                                />
                              ) : null} 
                            </MDBox>
                            <MDBox display={"flex"} flexDirection={"row"}>
                              <FormControlLabel label={"Show to user?"}
                                control={<Checkbox checked={question.show} onChange={(event) => setQuestionDisplay(index, questionId, event.target.checked)}/>}
                              />
                              <FormControlLabel label={"Response required?"}
                                control={<Checkbox checked={!question.changed} onChange={(event) => setQuestionRequired(index, questionId, event.target.checked)}/>}
                              />
                              <FormControlLabel label={"Set Active in Record Timeline?"}
                                control={<Checkbox checked={question.activeView} onChange={(event) => setQuestionAlwaysView(index, questionId, event.target.checked)}/>}
                              />
                            </MDBox>
                              
                            {question.type === "redcapForm" ? (
                            <MDBox sx={{display: "flex", flexDirection: "row", justifyContent: "flex-start", alignItems: "center", marginY: 1}}>
                              <TextField variant={"standard"} value={question.value} label={"Please Enter the Redcap Variable Here"} onChange={(event) => setTextQuestionValue(index, questionId, event.target.value)} rows={1} sx={{marginX: 1}} fullWidth>
                              </TextField>
                            </MDBox>
                            ) : null}
                            {question.type === "text" ? (
                            <MDBox sx={{display: "flex", flexDirection: "row", justifyContent: "flex-start", alignItems: "center", marginY: 1}}>
                              <TextField variant={"standard"} value={question.value} label={"Default Text Field"} onChange={(event) => setTextQuestionValue(index, questionId, event.target.value)} rows={4} sx={{marginX: 1}} fullWidth multiline>
                              </TextField>
                            </MDBox>
                            ) : null}
                            {question.type === "description" ? (
                            <MDBox sx={{display: "flex", flexDirection: "row", justifyContent: "flex-start", alignItems: "center", marginY: 1}}>
                              <TextField variant={"standard"} value={question.value} label={"Description Text Field"} onChange={(event) => setTextQuestionValue(index, questionId, event.target.value)} rows={4} sx={{marginX: 1}} fullWidth multiline>
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
                                    <FaPen />
                                  </IconButton>
                                  <IconButton color={"error"} onClick={() => deleteChoiceQuestionOption(index, questionId, letter)}>
                                    <FaXmark />
                                  </IconButton>
                                </MDBox>
                              })}
                            </MDBox>
                            ) : null}
                            {question.type === "cumulativeScore" ? (
                            <MDBox sx={{display: "flex", flexDirection: "row", justifyContent: "flex-start", alignItems: "center", marginY: 1}}>
                              
                              <Autocomplete
                                multiple value={question.list} options={contents.contents.reduce((cumulative, value) => {
                                  cumulative.push(...value.questions.filter((a) => a.type == "score").map((a) => a.text));
                                  return cumulative;
                                }, ["All Scores"])}
                                onChange={(event, value) => { setCumulativeScoreInclusion(index, questionId, value) }}
                                renderOption={(props, option) => <li {...props}>{option}</li>}
                                renderInput={(params) => (
                                  <FormField
                                    {...params}
                                    label={"Choose Question Label for Summation"}
                                    InputLabelProps={{ shrink: true }}
                                  />
                                )}
                                fullWidth
                              />
                            </MDBox>
                            ) : null}
                          </Grid>
                        );
                      })}
                      <Grid item xs={12}>
                        <MDBox p={2} style={{display: "flex", justifyContent: "space-around"}}>
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

