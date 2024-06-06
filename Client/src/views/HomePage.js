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
  CardContent,
} from "@mui/material";

import MDTypography from "components/MDTypography";

// Layout
import OnePageLayout from "layouts/OnePage";
import { SessionController } from "database/session-control";

export default function HomePage() {
  const server = SessionController.getServer();
  const connectionStatus = SessionController.getConnectionStatus();

  const [alert, setAlert] = useState(null);

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
            {"Brain Recording Analysis and Visualization Online V3.0"}
          </MDTypography>
          <MDTypography variant={"h4"} color={"black"} align={"center"} fontSize={24}>
            {"University of Florida, Fixel Institute for Neurological Diseases"}
          </MDTypography>
        </CardContent>
        <CardContent>
          <MDTypography variant={"h6"} color={"black"} align={"center"} fontSize={20}>
            {connectionStatus.status ? "Backend Server Connected" : "Backend Server not Found"}
          </MDTypography>
        </CardContent>
      </Card>

    </OnePageLayout>
  );
};