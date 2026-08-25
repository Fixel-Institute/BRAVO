/**
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useEffect, useState } from "react";

// @mui material components
import { 
  Card, CardContent,
} from "@mui/material";

import MDTypography from "components/MDTypography";

// Layout
import OnePageLayout from "layouts/OnePage";
import { SessionController } from "database/session-control";

export default function HomePage() {
  const [alert, setAlert] = useState(null);

  return (
    <OnePageLayout wide image={"https://parrish-mccall.com/wp-content/uploads/2019/10/Parrish-McCall_NDC-UF_Health_Night-Ext-2-2-e1636574511902.jpg"}>
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
            {"Fixel Institute for Neurological Diseases, University of Florida"}
          </MDTypography>
        </CardContent>
        <CardContent>
          <MDTypography variant={"h5"} color={"black"} align={"center"} fontSize={20}>
            {"Version 3.1.3"}
          </MDTypography>
        </CardContent>
      </Card>

    </OnePageLayout>
  );
};