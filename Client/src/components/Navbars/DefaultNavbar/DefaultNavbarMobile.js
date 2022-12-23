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

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

import DefaultNavbarLink from "./DefaultNavbarLink";

import { usePlatformContext, setContextState } from "context";
import { dictionary } from "assets/translation.js";

function DefaultNavbarMobile({ open, close }) {
  const { width } = open && open.getBoundingClientRect();

  const [ controller, dispatch ] = usePlatformContext();
  const { darkMode, language } = controller;

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
          name={dictionary.SimplifiedNavbar.ChangeLanguage[language]}
          onClick={() => toggleCollapse("LanguageMenu")} 
          collapse={collapse === "LanguageMenu" ? <ExpandLessIcon/> : <ExpandMoreIcon/>}
        />
        {collapse === "LanguageMenu" ? (
          <MDBox>
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
    </Menu>
  );
}

// Typechecking props for the DefaultNavbarMenu
DefaultNavbarMobile.propTypes = {
  open: PropTypes.oneOfType([PropTypes.bool, PropTypes.object]).isRequired,
  close: PropTypes.oneOfType([PropTypes.func, PropTypes.bool, PropTypes.object]).isRequired,
};

export default DefaultNavbarMobile;
