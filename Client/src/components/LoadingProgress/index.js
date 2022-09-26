import { useState, useEffect } from "react";

import {
  CircularProgress,
  Backdrop
} from "@mui/material";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

import { usePlatformContext } from "context";
import { dictionary } from "assets/translation";

export default function LoadingProgress() {
  const [ context, dispatch ] = usePlatformContext();
  const { language } = context;

  return (
    <Backdrop
      sx={{ color: '#FFFFFF', zIndex: (theme) => theme.zIndex.drawer + 1 }}
      open={true}
      onClick={() => {}}
    >
      <MDBox display={"flex"} alignItems={"center"} flexDirection={"column"}>
        <MDTypography color={"white"} fontWeight={"bold"} fontSize={30}>
          {dictionary.WarningMessage.Loading[language]}
        </MDTypography>
        <CircularProgress color={"info"} />
      </MDBox>
    </Backdrop>
  )
}