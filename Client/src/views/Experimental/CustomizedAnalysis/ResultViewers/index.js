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

import { SessionController } from "database/session-control";
import { usePlatformContext, setContextState } from "context.js";
import TimeDomainFigure from "./TimeDomainFigure";
import EventPSDs from "./EventPSDs";

import MDBox from "components/MDBox";
import { Grid } from "@mui/material";

function ResultViewer({data, type}) {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  if (Object.keys(data).length == 0) return null;

  if (type == "TimeSeries") {
    return <Grid container spacing={2}>
      <Grid item xs={12}>
        <TimeDomainFigure dataToRender={data} height={250} figureTitle={"TimeDomainFigure"} />
      </Grid>
      <Grid item xs={12} lg={6}>
        {Object.keys(data.Data.EventPSDs).length == 0 ? null : (
          <EventPSDs dataToRender={data} height={600} figureTitle={"EventPSDs"} channelName={"Test"} />
        )} 
      </Grid>
    </Grid>
  } else {
    return null;
  }
}

export default ResultViewer;
