/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useState, useEffect, createRef } from "react";

// react-router-dom components
import { Link, useNavigate } from "react-router-dom";

// @mui material components
import {
  Card,
  CardContent,
  Input,
  Checkbox,
  Dialog,
  DialogContent,
  DialogActions,
} from "@mui/material";

import MuiAlertDialog from "components/MuiAlertDialog";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDInput from "components/MDInput";
import MDButton from "components/MDButton";

// Layout
import PageLayout from "layouts/OnePage/PageLayout";

import InertiaSensorSpectrum from "./InertiaSensorSpectrum";

import { usePlatformContext, setContextState } from "context";
import { dictionary } from "assets/translation";

let background = require("assets/img/blue-universe-felix-mittermeier.jpg");

export default function InertiaSensorViewer() {
  const [context, dispatch] = usePlatformContext();
  const { language } = context;

  const navigate = useNavigate();

  const [alert, setAlert] = useState(null);
  const [dataToRender, setDataToRender] = useState([]);
  const [showResult, setShowResult] = useState(false);

  const fileInputRef = createRef();

  const handleUploadClicked = () => {
    if (fileInputRef.current && dataToRender.length == 0) {
      fileInputRef.current.click();
    }
  };

  const parseFileBinary = (files) => {
    for (let file of files) {
      let reader = new FileReader();
      reader.onload = () => {
        let header = reader.result.slice(0,80);
        const str = new TextDecoder().decode(header);
        if (str.startsWith("DATA:APPLEWATCH")) {
          let dataStruct = {
            accelerometer: {
              time: [],
              x: [],
              y: [],
              z: [],
            }, 
            tremorSeverity: {
              time: [],
              timeEnd: [],
              scales: [],
              value: [],
            },
            dyskinesiaProbability: {
              time: [],
              timeEnd: [],
              value: [],
            },
            heartRate: {
              time: [],
              value: []
            },
            heartRateVariability: {
              time: [],
              value: []
            },
            sleepState: {
              time: [],
              timeEnd: [],
              value: []
            }
          };

          let binaryLoader = new DataView( reader.result.slice(80) );
          let currentIndex = 0;
          while (currentIndex < binaryLoader.byteLength) {
            let dataType = binaryLoader.getUint8(currentIndex);
            switch (dataType) {
              case 125:
                dataStruct.accelerometer.x.push(binaryLoader.getInt16(currentIndex + 2, true)/1000);
                dataStruct.accelerometer.y.push(binaryLoader.getInt16(currentIndex + 4, true)/1000);
                dataStruct.accelerometer.z.push(binaryLoader.getInt16(currentIndex + 6, true)/1000);
                dataStruct.accelerometer.time.push(new Date(binaryLoader.getFloat64((currentIndex + 8), true)*1000));
                currentIndex += 16;
                break
              case 126: 
                let tremorScales = Array(6).fill(0).map((value, index)=>binaryLoader.getUint8(currentIndex + 1 + index, true)/100);
                dataStruct.tremorSeverity.scales.push(tremorScales);
                let tremorSeverity = 0;
                let totalScale = 0;
                tremorScales.map((value, index) => {
                  tremorSeverity += value * index;
                  if (index > 0) totalScale += value
                });

                if (totalScale > 0) {
                  dataStruct.tremorSeverity.value.push(tremorSeverity / totalScale);
                  dataStruct.tremorSeverity.time.push(new Date(binaryLoader.getFloat64((currentIndex + 16), true)*1000));
                }
                currentIndex += 24;
                break;
              case 127:
                dataStruct.dyskinesiaProbability.value.push(binaryLoader.getUint16(currentIndex + 2, true)/60000);
                dataStruct.dyskinesiaProbability.time.push(new Date(binaryLoader.getFloat64((currentIndex + 8), true)*1000));
                currentIndex += 16;
                break;
              case 128:
                dataStruct.heartRate.value.push(binaryLoader.getUint16(currentIndex + 2, true));
                dataStruct.heartRate.time.push(new Date(binaryLoader.getFloat64((currentIndex + 8), true)*1000));
                currentIndex += 16;
                break;
              case 129:
                dataStruct.heartRateVariability.value.push(binaryLoader.getUint16(currentIndex + 2, true));
                dataStruct.heartRateVariability.time.push(new Date(binaryLoader.getFloat64((currentIndex + 8), true)*1000));
                currentIndex += 16;
                break;
              case 130:
                dataStruct.sleepState.value.push(binaryLoader.getUint8(currentIndex + 1, true));
                let timeRange = binaryLoader.getUint16(currentIndex + 2, true);
                dataStruct.sleepState.time.push(new Date(binaryLoader.getFloat64((currentIndex + 8), true)*1000));
                dataStruct.sleepState.timeEnd.push(new Date(binaryLoader.getFloat64((currentIndex + 8), true)*1000 + timeRange*1000));
                currentIndex += 16;
                break;
              default: 
                throw new Error("File Format Incorrect");
            }
          }
          setDataToRender((dataToRender) => {
            return [...dataToRender, dataStruct];
          });
        }
      }
      reader.readAsArrayBuffer(file);
    }
  };

  const handleFileSelection = (event) => {
    setDataToRender([]);
    setShowResult(false);
    let files = fileInputRef.current.files;
    parseFileBinary(files);
  };
  
  useEffect(() => {
    if (dataToRender.length > 0) {
      if(fileInputRef.current.files.length == dataToRender.length) {
        setShowResult(true);
      }
    } 
  }, [dataToRender])

  return (
    <PageLayout>
      {alert}
      <MDBox pt={5} pb={5} px={15}
        position="absolute"
        width="100%"
        minHeight="100vh"
        sx={{
          backgroundImage: ({ functions: { linearGradient, rgba }, palette: { gradients } }) =>
          background &&
            `${linearGradient(
              rgba(gradients.dark.main, 0.6),
              rgba(gradients.dark.state, 0.6)
            )}, url(${background})`,
          backgroundSize: "fill",
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat",
        }}
      >
        <Card
          onClick={handleUploadClicked} 
          onDragOver={(event) => event.preventDefault()}
          onDragEnter={(event) => event.preventDefault()}
          onDrop={(event) => {
            fileInputRef.current.files = event.dataTransfer.files;
            handleFileSelection();
            event.preventDefault();
          }}
        sx={{
          borderRadius: "30px", 
          minHeight: "300px",
          backgroundColor: "#FFFFFF",
          cursor: "pointer",
        }}>
          <CardContent sx={{minHeight: 800, display: "flex"}}>
            <Input inputRef={fileInputRef} type={"file"} onChange={handleFileSelection} inputProps={{multiple: true}} slotProps={{root: {style: {display: "none"}}}}/>
            {showResult ? <InertiaSensorSpectrum dataToRender={showResult ? dataToRender : []} height={1500} figureTitle={"BRAVO Wearable Data Viewer"}/> : (
              <MDBox style={{height: "100%", marginTop: "auto", marginBottom: "auto", marginLeft: "auto", marginRight: "auto"}}>
                <MDTypography variant={"h4"} fontSize={36} textAlign={"center"}>
                  {"Drag and Drop Files to View"}
                </MDTypography>
              </MDBox>
            )}
          </CardContent>
        </Card>
      </MDBox>
      
    </PageLayout>
  );
};