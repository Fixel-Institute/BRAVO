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

// Material Dashboard 2 PRO React components
import MDTypography from "components/MDTypography";

// Layout
import OnePageLayout from "layouts/OnePage";

export default function HomePage() {

  return (
    <OnePageLayout wide image={"https://j9q7m2a3.rocketcdn.me/wp-content/uploads/2022/01/UF-Health.jpg"}>
      <Card sx={{
        paddingTop: 5,
        paddingBottom: 5,
        marginBottom: 5,
        borderRadius: "30px", 
        backgroundColor: "#AAAAAA77"
      }}>
        <CardContent>
          <MDTypography variant={"h2"} color={"black"} align={"center"} fontSize={48}>
            {"Brain Recording And Visualization Online"}
          </MDTypography>
          <MDTypography variant={"h4"} color={"black"} align={"center"} fontSize={24}>
            {"University of Florida, Fixel Institute for Neurological Diseases"}
          </MDTypography>
        </CardContent>
        <CardContent>
          <MDTypography variant={"h4"} color={"black"} align={"center"} fontSize={28}>
            {"Temporary Front Page"}
          </MDTypography>
        </CardContent>
      </Card>

    </OnePageLayout>
  );
};