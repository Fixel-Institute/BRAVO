/**
=========================================================
* Material Dashboard 2 React - v2.1.0
=========================================================

* Product Page: https://www.creative-tim.com/product/material-dashboard-react
* Copyright 2022 Creative Tim (https://www.creative-tim.com)

Coded by www.creative-tim.com

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
*/

import { useState } from "react";

// prop-types is a library for typechecking of props
import PropTypes from "prop-types";

// react-router components
import { Link } from "react-router-dom";

// @mui material components
import {
  Collapse, 
  Dialog,
  DialogContent,
  DialogActions,
  TextField,
  Grid,
  Menu,
  MenuItem,
  List, 
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Icon,
} from "@mui/material";
import MuiLink from "@mui/material/Link";

// MUI Icons
import LoginIcon from '@mui/icons-material/Login';
import GroupAddIcon from '@mui/icons-material/GroupAdd';
import ChangeCircleIcon from '@mui/icons-material/ChangeCircle';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import StorageIcon from '@mui/icons-material/Storage';
import CheckIcon from '@mui/icons-material/Check';

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";

import DefaultNavbarLink from "./DefaultNavbarLink";

import { SessionController } from 'database/session-control';
import { usePlatformContext, setContextState } from "context";
import { dictionary } from "assets/translation.js";
import { IMPORT } from "stylis";

function DefaultNavbarMobile({ open, close }) {
  const { width } = open && open.getBoundingClientRect();

  const [ controller, dispatch ] = usePlatformContext();
  const { darkMode, language } = controller;

  const [currentHost, setCurrentHost] = useState("Localhost");
  const [customServer, setCustomServer] = useState({show: false, address: ""});

  const [collapse, setCollapse] = useState("");
  const toggleCollapse = (name) => {
    if (collapse === name) {
      setCollapse("");
    } else {
      setCollapse(name);
    }
  };

  const setLanguage = (lang) => {
    if (lang === "English") {
      setContextState(dispatch, "language", "en");
    } else if (lang === "中文") {
      setContextState(dispatch, "language", "zh");
    }
    setCollapse("");
  };

  const setServer = (server) => {
    setCollapse("");

    if (server == "Localhost") {
      SessionController.setServer("http://localhost:3001");
      window.location.reload();

    } else if (server == "DemoServer") {
      SessionController.setServer("https://bravo-server.jcagle.solutions");
      window.location.reload();

    } else {
      if (customServer.show) {
        SessionController.setServer(customServer.address);
        window.location.reload();

      } else {
        setCustomServer({address: "", show: true});
      }

    }
  };

  return (
    <Menu
      getContentAnchorEl={null}
      anchorOrigin={{
        vertical: "bottom",
        horizontal: "center",
      }}
      transformOrigin={{
        vertical: "top",
        horizontal: "center",
      }}
      anchorEl={open}
      open={Boolean(open)}
      onClose={close}
      MenuListProps={{ style: { width: `calc(${width}px - 4rem)` } }}
    >
      <MDBox px={0.5}>
        <DefaultNavbarLink 
          icon={<ChangeCircleIcon/>}
          name={dictionary.SimplifiedNavbar.ChangeServer[language]}
          onClick={() => toggleCollapse("ServerMenu")} 
          collapse={collapse === "ServerMenu" ? <ExpandLessIcon/> : <ExpandMoreIcon/>}
        />
        {collapse === "ServerMenu" ? (
          <MDBox style={{marginLeft: 10}}>
            {["Localhost","DemoServer","CustomizedServer"].map((server) => (
              <MenuItem key={server} onClick={() => setServer(server)}>
                <Icon sx={{ mr: 1 }}>{
                  currentHost === server ? (
                    <CheckIcon/>
                  ) : (
                    <StorageIcon/>
                  )
                }</Icon>
                <MDTypography variant="button" fontWeight="regular" color="text">
                  {dictionary.SimplifiedNavbar[server][language]}
                </MDTypography>
              </MenuItem>
            ))}
          </MDBox>
        ) : null}
        <DefaultNavbarLink 
          icon={<ChangeCircleIcon/>}
          name={dictionary.SimplifiedNavbar.ChangeLanguage[language]}
          onClick={() => toggleCollapse("LanguageMenu")} 
          collapse={collapse === "LanguageMenu" ? <ExpandLessIcon/> : <ExpandMoreIcon/>}
        />
        {collapse === "LanguageMenu" ? (
          <MDBox style={{marginLeft: 10}}>
            {["English","中文"].map((lang) => (
              <MenuItem key={lang} onClick={() => setLanguage(lang)}>
                <MDTypography variant="button" fontWeight="regular" color="text">
                  {lang}
                </MDTypography>
              </MenuItem>
            ))}
          </MDBox>
        ) : null}
        <DefaultNavbarLink
          icon={<LoginIcon/>}
          name={dictionary.SimplifiedNavbar.Login[language]}
          route="/login"
        />
        <DefaultNavbarLink
          icon={<GroupAddIcon/>}
          name={dictionary.SimplifiedNavbar.Register[language]}
          route="/register"
        />
      </MDBox>

      <Dialog open={customServer.show} onClose={() => setCustomServer({...customServer, show: false})}>
        <MDBox px={2} pt={2} sx={{minWidth: 500}}>
          <MDTypography variant="h5">
            {"Set Custom Server Address"}
          </MDTypography>
        </MDBox>
        <DialogContent>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                variant="standard"
                margin="dense"
                placeholder="Server Address (i.e.: http://localhost:3001)"
                value={customServer.address}
                onChange={(event) => setCustomServer({...customServer, address: event.target.value})}
                fullWidth
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <MDBox style={{marginLeft: "auto", paddingRight: 5}}>
            <MDButton color={"secondary"} 
              onClick={() => setCustomServer({...customServer, show: false})}
            >
              Cancel
            </MDButton>
            <MDButton color={"info"} 
              onClick={() => setServer()} style={{marginLeft: 10}}
            >
              Update
            </MDButton>
          </MDBox>
        </DialogActions>
      </Dialog>
    </Menu>
  );
}

// Typechecking props for the DefaultNavbarMenu
DefaultNavbarMobile.propTypes = {
  open: PropTypes.oneOfType([PropTypes.bool, PropTypes.object]).isRequired,
  close: PropTypes.oneOfType([PropTypes.func, PropTypes.bool, PropTypes.object]).isRequired,
};

export default DefaultNavbarMobile;
