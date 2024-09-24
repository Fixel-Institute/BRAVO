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

// @mui material components
import { 
  Card, 
  CardHeader, 
  CardContent,
  Switch,
  Grid,
  Link,
} from "@mui/material";

import MDTypography from "components/MDTypography";

// Layout
import OnePageLayout from "layouts/OnePage";

import { SessionController } from "database/session-control";

import MuiAlertDialog from "components/MuiAlertDialog";

export default function HomePage() {
  const server = SessionController.getServer();
  const connectionStatus = SessionController.getConnectionStatus();

  const [alert, setAlert] = useState(null);

  useEffect(() => {
    if (SessionController.getServer() == "https://bravo-server.jcagle.solutions") {
      setAlert(<MuiAlertDialog title={"Demo Server Disabled"} message={<>
        {"The demo version is currently disabled per request from third-party medical device company. "}
        {"If you would like to try out the system, please refers to "}
        <Link target="_blank" href="https://bravo-documentation.jcagle.solutions/installation" underline="always" sx={{color: "blue"}} > <i>the installation guide</i> </Link>
        {"to obtain a local offline version. "}
        <br></br>
      </>}
        handleClose={() => setAlert()} 
        handleConfirm={() => setAlert()}/>)
    } else if (connectionStatus.status) {
      
    }
  }, []);

  return (
    <OnePageLayout wide image={"https://j9q7m2a3.rocketcdn.me/wp-content/uploads/2022/01/UF-Health.jpg"}>
      {alert}
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
            {connectionStatus.status ? "Backend Server Connected" : "Backend Server not Found"}
            <br></br>
            {"Host: " + (server || (window.location.protocol + "//" + window.location.hostname))}
          </MDTypography>
          {connectionStatus.status && connectionStatus.version? (
            <MDTypography variant={"h4"} color={"black"} align={"center"} fontSize={24} pt={2}>
              {"Current Docker Version: " + new Date(connectionStatus.version*1000).toLocaleString()}
            </MDTypography>
          ) : null}
          {connectionStatus.status && connectionStatus.version? (
            <MDTypography variant={"h4"} color={"black"} align={"center"} fontSize={24} pt={2}>
              {"Latest Docker Version: " + new Date(connectionStatus.update*1000).toLocaleString()}
            </MDTypography>
          ) : null}
        </CardContent>
      </Card>

    </OnePageLayout>
  );
};