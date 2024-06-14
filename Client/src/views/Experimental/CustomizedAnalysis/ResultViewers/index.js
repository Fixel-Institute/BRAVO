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
import SpectralFeatures from "./SpectralFeatures";

function ResultViewer({data, result}) {
  const navigate = useNavigate();
  const [controller, dispatch] = usePlatformContext();
  const { patientID, language } = controller;

  if (Object.keys(data).length == 0) return null;
  const type = data.Data[0].ResultType;

  if (type == "PSDs") {
    return <Grid container spacing={2}>
      <Grid item xs={12}>
        <EventPSDs dataToRender={data.Data[0]} height={600} figureTitle={"EventPSDs"} />
      </Grid>
    </Grid>
  } else if (type == "SpectralFeatures") {
    return <Grid container spacing={2}>
      <Grid item xs={12}>
        <SpectralFeatures dataToRender={data.Data[0].Features} height={600} figureTitle={result.title} />
      </Grid>
    </Grid>
    return null;
  } else {
    return null
  }
}

export default ResultViewer;
