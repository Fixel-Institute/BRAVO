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
        {"As requested by Medtronic (Medtronic plc, MN), the demo server is effectively disabled and will not be accessible by public in the future. "}
        {"If you would like to try out the system, please refers to "}
        <Link target="_blank" href="https://bravo-documentation.jcagle.solutions/installation" underline="always" sx={{color: "blue"}} > <i>the installation guide</i> </Link>
        {"to obtain a local version for testing. "}
        <br></br>
        <br></br>
        {"The BRAVO Platform is expected to undergo significant adjustment to remove all references to copyright/trademark terminologies in accordance with the request from Medtronic."}
      </>}
        handleClose={() => setAlert()} 
        handleConfirm={() => setAlert()}/>)
    } else if (connectionStatus.status) {
      if (connectionStatus.version !== "2.2.3") {
        setAlert(<MuiAlertDialog title={"Server Version Imcompatible"} message={<>
          {"Current frontend page support Version 2.2.3. Please upgrade your server by following instructions at"}
          <Link target="_blank" href="https://bravo-documentation.jcagle.solutions/Tutorials/MigrationGuide2.1" underline="always" sx={{color: "blue"}} > <i>GitHub Page</i> </Link>
          <br></br>
          <br></br>
          {"If you would like to stay with older build, please use"}
          <Link target="_blank" href="https://bravo-documentation.jcagle.solutions/previous_builds" underline="always" sx={{color: "blue"}} > <i>this link</i> </Link>
          {"to access previous build links"}
          <br></br>
          <br></br>
          {"Additionally, you can run your local version using NPM with instructions at "}
          <Link target="_blank" href="https://bravo-documentation.jcagle.solutions/installation#react-frontend-installation-guide" underline="always" sx={{color: "blue"}} > <i>documentation page</i> </Link>
        </>}
          handleClose={() => setAlert()} 
          handleConfirm={() => setAlert()}/>)
      }
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
          <MDTypography variant={"h4"} color={"black"} align={"center"} fontSize={24} pt={2}>
            {"Current Frontend Version: 2.2.2"}
            <br></br>
            {"Connected Backend Version: "} {connectionStatus.version === "" ? "Unknown" : connectionStatus.version}
          </MDTypography>
        </CardContent>
      </Card>

    </OnePageLayout>
  );
};