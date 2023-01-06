import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  TextField,
  Autocomplete,
  Card,
  Grid,
  Modal,
  ListItemButton,
  ListItemText,
  ListItemIcon
} from "@mui/material";

import { ViewInAr, Timeline } from "@mui/icons-material";

import React from "react";
import * as THREE from "three";
import { Canvas, useThree } from '@react-three/fiber';

import colormap from "colormap";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import RadioButtonGroup from "components/RadioButtonGroup";
import MDBadge from "components/MDBadge";
import MDButton from "components/MDButton";
import FormField from "components/MDInput/FormField";
import LoadingProgress from "components/LoadingProgress";

// core components
import {
  CameraController,
  CoordinateSystem,
  ShadowLight,
  Model,
  Tractography,
  VolumetricObject,
  retrieveModels
} from "graphing-utility/Volumetric";

import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import { dictionary, dictionaryLookup } from "assets/translation.js";

function ImageVisualization() {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  const [existingFiles, setExistingFiles] = useState(false);
  const [availableItems, setAvailableItems] = React.useState([]);
  const [controlItems, setControlItems] = React.useState([]);

  const [addItemModal, setAddItemModal] = useState({show: false});

  const [cameraLock, setCameraLock] = React.useState(false);
  const [worldMatrix, setWorldMatrx] = React.useState(null);
  
  const [alert, setAlert] = useState(null);

  useEffect(() => {
    const matrix = new THREE.Matrix4();
    matrix.set(1, 0, 0, 0,
               0, 0, 1, 0,
               0, -1, 0, 0,
               0, 0, 0, 1);
    setWorldMatrx(matrix);
  }, []);

  useEffect(() => {
    if (!patientID) {
      navigate("/dashboard", {replace: false});
    } else {
      setAlert(<LoadingProgress/>);
      SessionController.query("/api/queryImageDirectory", {
        id: patientID
      }).then((response) => {
        setAvailableItems(response.data);
        setAlert(null);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  const checkItemIndex = (item) => {
    for (var i in availableItems) {
      if (availableItems[i].filename == item.filename) return i; 
    }
  };

  const addModel = (item) => {
    if (!item.downloaded) {
      retrieveModels(patientID, item).then((data) => {
        if (item.type === "electrode") {
          var electrodeCount = 0;
          for (var i in controlItems) {
            if (controlItems[i].type == "electrode") {
              electrodeCount++;
            }
          }
          data[0].filename += " " + electrodeCount.toString();
        } else {
          const index = checkItemIndex(item);    
          availableItems[index].downloaded = true;
          setAvailableItems(availableItems);
        }
        setControlItems([...controlItems, ...data]);
      });
    } else {
      for (var i in controlItems) {
        if (controlItems[i].filename == item.filename) {
          controlItems[i].show = !controlItems[i].show;
        }
      }
      setControlItems([...controlItems]);
    }
    setAddItemModal({...addItemModal, show: false});
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
                      <MDBox display={"flex"} justifyContent={"space-between"} p={2}>
                        <MDTypography variant={"h6"} fontSize={24}>
                          {dictionary.ImageVisualization.Title[language]}
                        </MDTypography>
                        <MDBox display={"flex"} flexDirection={"column"}>
                          <MDButton size="medium" variant="contained" color="info" onClick={() => setAddItemModal({...addItemModal, show: true})}>
                            {dictionaryLookup(dictionary.ImageVisualization, "AddItem", language)}
                          </MDButton>
                        </MDBox>
                      </MDBox>

                      <Modal 
                        open={addItemModal.show}
                        onClose={() => setAddItemModal({...addItemModal, show: false})}
                      >
                        <MDBox sx={{
                          position: 'absolute',
                          top: '50%',
                          left: '50%',
                          transform: 'translate(-50%, -50%)',
                          width: 400,
                          maxHeight: 600,
                          overflow: "auto",
                          bgcolor: 'background.paper',
                          border: '2px solid #000',
                          boxShadow: 24,
                          p: 4,
                        }}>
                          <MDTypography variant="h6" component="h2">
                            Add Objects or Tracts
                          </MDTypography>
                          <MDBox>
                            <Grid container spacing={2}>
                              {availableItems.map((item) => {
                                return <Grid item xs={12} key={item.file} style={{background: item.show ? "#a2cf6e" : ""}}>
                                  <ListItemButton onClick={() => addModel(item)}>
                                    <ListItemIcon>
                                      {item.type === "stl" ? <ViewInAr /> : null}
                                      {item.type === "points" ? <Timeline /> : null}
                                      {item.type === "tracts" ? <Timeline /> : null}
                                      {item.type === "electrode" ? <ViewInAr /> : null}
                                    </ListItemIcon>
                                    <ListItemText primary={item.file} />
                                  </ListItemButton>
                                </Grid>
                              })}
                            </Grid>
                          </MDBox>
                        </MDBox>
                      </Modal>

                    </Grid>
                    <Grid item xs={12}>
                      <MDBox p={2}>
                        <Canvas style={{height: "100%", height: "60vh", background: "#000000"}}>
                          <CameraController cameraLock={cameraLock}/>
                          <CoordinateSystem length={50} origin={[300, -300, -150]}/>
                          <ShadowLight x={-100} y={-100} z={-100} color={0xffffff} intensity={0.5}/>
                          <ShadowLight x={100} y={100} z={100} color={0xffffff} intensity={0.5}/>
                          <hemisphereLight args={[0xffffff, 0xffffff, 0.2]} color={0x3385ff} groundColor={0xffc880} position={[0, 100, 0]} />
                          <hemisphereLight args={[0xffffff, 0xffffff, 0.2]} color={0x3385ff} groundColor={0xffc880} position={[0, -100, 0]} />
                          <group matrixAutoUpdate={false} matrix={worldMatrix}>
                            {controlItems.map((item) => {
                              if (item.data && item.show) {
                                if (item.type === "stl") {
                                  return <Model key={item.filename} geometry={item.data} material={{
                                    color: item.color,
                                    specular: 0x111111,
                                    shininess: 200,
                                    opacity: item.opacity
                                  }} matrix={item.matrix}></Model>
                                } else if (item.type === "electrode") {
                                  return <group key={item.filename}>
                                    {item.data.map((value, index) => {
                                      return <Model key={item.subname[index]} geometry={value} material={{
                                        color: item.subname[index].endsWith("_shaft.stl") ? item.color : "#FFFFFF",
                                        specular: 0x111111,
                                        shininess: 200,
                                        opacity: item.opacity
                                      }} matrix={item.matrix}></Model>
                                    })}
                                  </group>
                                } else if (item.type === "points") {
                                  return item.data.map((arrayPoints, index) => {
                                    return <Tractography key={item.filename + index} pointArray={arrayPoints} color={item.color} linewidth={item.thickness} matrix={item.matrix}/>
                                  })
                                } else if (item.type === "tracts") {
                                  return item.data.map((arrayPoints, index) => {
                                    return <Tractography key={item.filename + index} pointArray={arrayPoints} color={item.color} linewidth={item.thickness} matrix={item.matrix}/>
                                  })
                                } else if (item.type === "volume") {
                                  return <VolumetricObject key={item.filename} data={item.data} matrix={worldMatrix} cameraLock={cameraLock} />
                                }
                              }
                            })}
                          </group>
                        </Canvas>
                      </MDBox>
                    </Grid>
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

export default ImageVisualization;
