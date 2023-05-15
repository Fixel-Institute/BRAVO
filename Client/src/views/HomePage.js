/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useState } from "react";
import { Link } from "react-router-dom";

// @mui material components
import { 
  Card, 
  CardHeader, 
  CardContent,
  Switch,
  Grid,
  MuiLink,
} from "@mui/material";

import MDTypography from "components/MDTypography";

// Layout
import OnePageLayout from "layouts/OnePage";

import { SessionController } from "database/session-control";

export default function HomePage() {
  const server = SessionController.getServer();
  const connectionStatus = SessionController.getConnectionStatus();

  return (
    <OnePageLayout wide image={"https://j9q7m2a3.rocketcdn.me/wp-content/uploads/2022/01/UF-Health.jpg"}>
      <Card sx={{
        paddingTop: 5,
        paddingBottom: 5,
        marginTop: 15,
        marginBottom: 15,
        borderRadius: "30px", 
        backgroundColor: "#AAAAAA77"
      }}>
        <CardContent>
          <MDTypography variant={"h2"} color={"black"} align={"center"} fontSize={48}>
            {"Brain Recording Analysis and Visualization Online"}
          </MDTypography>
          <MDTypography variant={"h4"} color={"black"} align={"center"} fontSize={24}>
            {"University of Florida, Fixel Institute for Neurological Diseases"}
          </MDTypography>
        </CardContent>
        <CardContent>
          <MDTypography variant={"h4"} color={"black"} align={"center"} fontSize={28}>
            {"Connection Status"}
          </MDTypography>
          <MDTypography variant={"h6"} color={"black"} align={"center"} fontSize={20}>
            {connectionStatus ? "Backend Server Connected" : "Backend Server not Found"}
            <br></br>
            {"Host: " + (server || (window.location.protocol + "//" + window.location.hostname))}
          </MDTypography>
          <MDTypography variant={"h4"} color={"black"} align={"center"} fontSize={24} pt={2}>
            {"Current Frontend Version: 2.2.0"}
            <br></br>
            {"Compatible Backend Version: 2.2.0"}
          </MDTypography>
        </CardContent>
      </Card>

    </OnePageLayout>
  );
};