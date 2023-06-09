/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  TextField,
  Autocomplete,
  Dialog,
  DialogContent,
  Popover,
  Card,
  Grid,
  Modal,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  IconButton,
} from "@mui/material";

import { ViewInAr, Timeline } from "@mui/icons-material";
import { TwitterPicker, BlockPicker } from "react-color";

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
  retrieveModels,
  computeElectrodePlacement
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
  const [descriptor, setDescriptor] = React.useState({});

  const [addItemModal, setAddItemModal] = useState({show: false});
  const [popup, setPopupState] = React.useState({item: ""});
  const [editTargetEntry, setEditTargetEntry] = React.useState({show: false, item: "", targetPoint: [0,0,0], entryPoint: [10,10,10]});

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
        setAvailableItems(response.data.availableModels);
        setDescriptor(response.data.descriptor);
        setAlert(null);
      }).catch((error) => {
        SessionController.displayError(error, setAlert);
      });
    }
  }, [patientID]);

  useEffect(() => {
    //downloadModelsFromDescriptor();
  }, [availableItems, descriptor]);

  const downloadModelsFromDescriptor = async () => {
    setAlert(<LoadingProgress/>);
    let allItems = [];
    const files = Object.keys(descriptor);
    for (let item of availableItems) {
      if (files.includes(item.file)) {
        if (!item.downloaded) {
          const data = await retrieveModels(patientID, item, descriptor[item.file].color);
          if (item.type === "electrode") {
            if (descriptor[item.file].targetPoint) data[0].targetPts = descriptor[item.file].targetPoint;
            if (descriptor[item.file].entryPoint) data[0].entryPts = descriptor[item.file].entryPoint;
          } else {
            const index = checkItemIndex(item);    
            availableItems[index].downloaded = true;
          }
          allItems = [...allItems, ...data];
        }
      }
    }
    setControlItems(allItems);
    setAvailableItems(availableItems);
    setAlert(null);
  }

  const checkItemIndex = (item) => {
    for (var i in availableItems) {
      if (availableItems[i].file == item.file) return i; 
    }
  };

  const addModel = async (item, color) => {
    if (!item.downloaded) {
      const data = await retrieveModels(patientID, item, color);
      if (item.type === "electrode") {
        var electrodeCount = 0;
        for (var i in controlItems) {
          if (controlItems[i].type == "electrode") {
            electrodeCount++;
          }
        }
      }

      const index = checkItemIndex(item);
      availableItems[index].downloaded = true;
      setAvailableItems(availableItems);
      setControlItems([...controlItems, ...data]);
    } else {
      for (var i in controlItems) {
        if (controlItems[i].filename == item.file) {
          controlItems[i].show = !controlItems[i].show;
        }
      }
      setControlItems([...controlItems]);
    }
    setAddItemModal({...addItemModal, show: false});
  };

  const updateObjectColor = (filename, color) => {
    for (var i in controlItems) {
      if (controlItems[i].filename == filename) {
        controlItems[i].color = color.hex;
        break;
      }
    }
    setControlItems([...controlItems]);
  };

  const updateTargetPoints = () => {
    setControlItems((controlItems) => {
      for (let i in controlItems) {
        if (controlItems[i].filename == editTargetEntry.file) {
          controlItems[i].targetPts = editTargetEntry.targetPoint.map((value) => parseFloat(value));
          controlItems[i].entryPts = editTargetEntry.entryPoint.map((value) => parseFloat(value));
        }
      }
      return [...controlItems];
    });
    setEditTargetEntry({...editTargetEntry, show: false});
  };

  const lockCamera = () => {
    setCameraLock((cameraLock) => {
      return !cameraLock;
    });
  }

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
                      <Grid container>
                        {availableItems.map((item) => {
                          let downloadedItem = null;
                          for (let i in controlItems) {
                            if (controlItems[i].filename == item.file) {
                              downloadedItem = controlItems[i]
                            }
                          }

                          return <Grid item xs={12} sm={6} md={4}>
                            <MDBox px={2} style={{display: "flex", flexDirection: "row", alignItems: "center"}}>
                              {downloadedItem ? (
                                <>
                                  <IconButton
                                    style={{padding: 0, marginRight: 3, borderStyle: "solid", borderColor: "#000000", borderWidth: 1, height: "100%"}} 
                                    onClick={(event) => setPopupState({item: item.file, anchorEl: event.currentTarget})}
                                  >
                                    <img style={{background: downloadedItem.color, padding: 8, borderRadius: "50%"}}/>
                                  </IconButton>
                                  <Popover 
                                    open={popup.item == item.file}
                                    onClose={() => setPopupState({item: "", anchorEl: null})}
                                    anchorEl={popup.anchorEl}
                                    anchorOrigin={{
                                      vertical: 'bottom',
                                      horizontal: 'left',
                                    }}
                                    transformOrigin={{
                                      vertical: "top",
                                      horizontal: 'left',
                                    }}
                                    PaperProps={{sx: {boxShadow: "none"}}}
                                  >
                                    <TwitterPicker color={downloadedItem.color} onChange={(color) => updateObjectColor(item.file, color)}/>
                                  </Popover>
                                </>
                              ) : null}
                              <MDTypography variant="h6" fontSize={15} color={downloadedItem ? "dark" : "light"} style={{cursor: "pointer"}} onClick={() => addModel(item)}>
                                {item.file}
                              </MDTypography>
                              {downloadedItem ? (<IconButton variant="contained" color={downloadedItem.show ? "info" : "light"} onClick={() => addModel(item)}>
                                <i className="fa-solid fa-eye" style={{fontSize: 10}}></i>
                              </IconButton>) : null}
                              {downloadedItem && item.type === "electrode" ? (<IconButton variant="contained" color={"info"} onClick={() => setEditTargetEntry({item: item.file, targetPoint: item.targetPt, entryPoint: item.entryPt, show: true})}>
                                <i className="fa-solid fa-pen" style={{fontSize: 10}}></i>
                              </IconButton>) : null}
                              {downloadedItem && item.type === "volume" ? (<IconButton variant="contained" color={cameraLock ? "light" : "info"} onClick={lockCamera}>
                                <i className="fa-solid fa-pen" style={{fontSize: 10}}></i>
                              </IconButton>) : null}
                            </MDBox>
                          </Grid>
                        })}
                      </Grid>
                    </Grid>
                    <Grid item xs={12}>
                      <MDBox p={2}>
                        <Canvas style={{height: "100%", height: "80vh", background: "#000000"}}>
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
                                  let matrix = computeElectrodePlacement(item.targetPts, item.entryPts);
                                  return <group key={item.filename}>
                                    {item.data.map((value, index) => {
                                      return <Model key={item.subname[index]} geometry={value} material={{
                                        color: item.subname[index].endsWith("shaft.stl") ? item.color : "#FFFFFF",
                                        specular: 0x111111,
                                        shininess: 200,
                                        opacity: item.opacity
                                      }} matrix={matrix}></Model>
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
          <Dialog open={editTargetEntry.show} onClose={() => setEditTargetEntry({...editTargetEntry, show: false})}>
            <MDBox px={2} pt={2}>
              <MDTypography variant="h5">
                {"Edit Electrode Target/Entry Points"}
              </MDTypography>
              <MDTypography variant="p" fontSize={24}>
                {editTargetEntry.item}
              </MDTypography>
            </MDBox>
            <DialogContent style={{minWidth: 500}} >
              <MDBox style={{display: "flex", flexDirection: "row"}}>
                {editTargetEntry.targetPoint.map((value, index) => {
                  let coordinate = ["x", "y", "z"];
                  return <TextField
                    variant="standard"
                    margin="dense"
                    value={editTargetEntry.targetPoint[index]}
                    onChange={(event) => setEditTargetEntry((editTargetEntry) => {
                      editTargetEntry.targetPoint[index] = event.target.value;
                      return {...editTargetEntry};
                    })}
                    label={"Target Position " + coordinate[index] + ":"} type={"number"}
                    autoComplete={"off"}
                    fullWidth
                  />
                })}
              </MDBox>

              <MDBox style={{display: "flex", flexDirection: "row"}}>
                {editTargetEntry.entryPoint.map((value, index) => {
                  let coordinate = ["x", "y", "z"];
                  return <TextField
                    variant="standard"
                    margin="dense"
                    value={editTargetEntry.entryPoint[index]}
                    onChange={(event) => setEditTargetEntry((editTargetEntry) => {
                      editTargetEntry.entryPoint[index] = event.target.value;
                      return {...editTargetEntry};
                    })}
                    label={"Entry Position " + coordinate[index] + ":"} type={"number"}
                    autoComplete={"off"}
                    fullWidth
                  />
                })}
              </MDBox>
            </DialogContent>
            <MDBox px={2} py={2} style={{display: "flex", justifyContent: "flex-end"}}>
              <MDButton variant={"gradient"} color={"secondary"} onClick={() => setEditTargetEntry({...editTargetEntry, show: false})}>
                {"Cancel"}
              </MDButton>
              <MDButton variant={"gradient"} color={"success"} style={{marginLeft: 10}} onClick={updateTargetPoints}>
                {"Update"}
              </MDButton>
            </MDBox>
          </Dialog>
        </MDBox>
      </DatabaseLayout>
    </>
  );
}

export default ImageVisualization;
