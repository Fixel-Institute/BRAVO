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

import { useState, useEffect } from "react";

// react-router components
import { useLocation, Link, useNavigate } from "react-router-dom";

// prop-types is a library for typechecking of props.
import PropTypes from "prop-types";

// @material-ui core components
import { 
  AppBar,
  Avatar,
  Toolbar,
  Icon,
  IconButton,
  Menu
} from "@mui/material";
import TranslateIcon from '@mui/icons-material/Translate';
import ChangeCircleIcon from "@mui/icons-material/ChangeCircle";

// Material Dashboard 2 PRO React components
import MDBox from "components/MDBox";
import MDInput from "components/MDInput";
import MDBadge from "components/MDBadge";

// Material Dashboard 2 PRO React examples
import Breadcrumbs from "components/Breadcrumbs";
import NotificationItem from "components/Items/NotificationItem";

// Custom styles for DashboardNavbar
import {
  navbar,
  navbarContainer,
  navbarRow,
  navbarIconButton,
  navbarMobileMenu,
} from "components/Navbars/DashboardNavbar/styles";

//  BRAVO context
import { usePlatformContext, setContextState } from "context";
import { dictionary } from "assets/translation";
import { SessionController } from "database/session-control";

function DashboardNavbar({ absolute, light, isMini, fixedNavbar }) {
  const navigate = useNavigate();
  const [navbarType, setNavbarType] = useState();
  const [controller, dispatch] = usePlatformContext();
  const { miniSidenav, hideSidenav, transparentNavbar, darkMode, language } = controller;
  const [openMenu, setOpenMenu] = useState(false);
  const [whichMenu, setWhichMenu] = useState("");
  const route = useLocation().pathname.split("/").slice(1);

  function handleTransparentNavbar() {
    setContextState(dispatch, "transparentNavbar", (fixedNavbar && window.scrollY === 0) || !fixedNavbar);
  }

  useEffect(() => {
    // Setting the navbar type
    if (fixedNavbar) {
      setNavbarType("sticky");
    } else {
      setNavbarType("static");
    }
    
    // A function that sets the transparent state of the navbar.
    /*
    handleTransparentNavbar();
    window.addEventListener("scroll", handleTransparentNavbar);
    return () => window.removeEventListener("scroll", handleTransparentNavbar);
    */
  }, [dispatch, fixedNavbar]);

  const handleHideSidenav = () => {
    setContextState(dispatch, "hideSidenav", !hideSidenav);
  };
  const handleMiniSidenav = () => setContextState(dispatch, "miniSidenav", !miniSidenav);
  const handleOpenMenu = (event, name) => {
    setOpenMenu(event.currentTarget);
    setWhichMenu(name);
  }
  const handleCloseMenu = () => {
    setWhichMenu("");
    setOpenMenu(null);
  };

  const logoutUser = () => {
    SessionController.logout().then((response) => {
      SessionController.nullifyUser();
      setContextState(dispatch, "user", {});
      setContextState(dispatch, "patientID", null);
      navigate("/", {replace: true});
    }).catch((error) => {
      console.log(error)
    })
  };

  // Render the notifications menu
  const renderProfileMenu = () => (
    <Menu
      anchorEl={openMenu}
      anchorReference={null}
      disableScrollLock
      anchorOrigin={{
        vertical: "bottom",
        horizontal: "left",
      }}
      open={whichMenu === "ProfileMenu"}
      onClose={handleCloseMenu}
      sx={{ mt: 2 }}
    >
      <NotificationItem icon={<i className="fa-solid fa-address-card"></i>} title={dictionary.SimplifiedNavbar.Profile[language]} />
      <NotificationItem icon={<i className="fa-solid fa-arrow-right-from-bracket"></i>} title={dictionary.SimplifiedNavbar.Logout[language]} 
        onClick={() => logoutUser()}/>
    </Menu>
  );

  const setLanguage = (lang) => {
    if (lang === "English") {
      setContextState(dispatch, "language", "en");
    } else if (lang === "中文") {
      setContextState(dispatch, "language", "zh");
    }
    handleCloseMenu();
  };

  // Render the notifications menu
  const renderLanguageSelectionMenu = () => (
    <Menu
      anchorEl={openMenu}
      anchorReference={null}
      anchorOrigin={{
        vertical: "bottom",
        horizontal: "left",
      }}
      open={whichMenu === "LanguageMenu"}
      onClose={handleCloseMenu}
      sx={{ mt: 2 }}
    >
      {["English","中文"].map((lang) => (
        <NotificationItem key={lang} title={lang} icon={<Icon sx={{ mr: 1 }}><ChangeCircleIcon/></Icon>} onClick={() => setLanguage(lang)}/>
      ))}
    </Menu>
  );

  // Styles for the navbar icons
  const iconsStyle = ({ palette: { dark, white, text }, functions: { rgba } }) => ({
    color: () => {
      let colorValue = light || darkMode ? white.main : dark.main;

      if (transparentNavbar && !light) {
        colorValue = darkMode ? rgba(text.main, 0.6) : text.main;
      }

      return colorValue;
    },
  });

  return (
    <AppBar
      position={absolute ? "absolute" : navbarType}
      color="inherit"
      sx={(theme) => navbar(theme, { transparentNavbar, absolute, light, darkMode })}
    >
      <Toolbar sx={(theme) => navbarContainer(theme)}>
        <MDBox color="inherit" mb={{ xs: 1, md: 0 }} sx={(theme) => navbarRow(theme, { isMini })}>
          <Breadcrumbs icon="home" title={route[route.length - 1]} route={route} light={light} />
          <IconButton onClick={handleMiniSidenav} size="small" disableRipple>
            <Icon fontSize="medium" sx={iconsStyle}>
              {!miniSidenav ? "menu_open" : "menu"}
            </Icon>
          </IconButton>
          <IconButton
            size="small"
            disableRipple
            color="inherit"
            sx={navbarMobileMenu}
            onClick={handleHideSidenav}
          >
            <Icon sx={iconsStyle} fontSize="medium">
              {!hideSidenav ? "menu_open" : "menu"}
            </Icon>
          </IconButton>
        </MDBox>
        {isMini ? null : (
          <MDBox sx={(theme) => navbarRow(theme, { isMini })}>
            <MDBox pr={1}>
              
            </MDBox>
            <MDBox color={light ? "white" : "inherit"}>
              <IconButton
                size="small"
                disableRipple
                color="inherit"
                sx={navbarIconButton}
                aria-controls="notification-menu"
                aria-haspopup="true"
                variant="contained"
                onClick={(event) => handleOpenMenu(event, "LanguageMenu")}
              >
                <TranslateIcon fontSize="large" />
              </IconButton>
              <IconButton
                size="small"
                disableRipple
                color="inherit"
                sx={navbarIconButton}
                aria-controls="notification-menu"
                aria-haspopup="true"
                variant="contained"
                onClick={(event) => handleOpenMenu(event, "ProfileMenu")}
              >
                <MDBadge badgeContent={9} color="error" size="xs" circular>
                  <Avatar src={""} />
                </MDBadge>
              </IconButton>
              {renderProfileMenu()}
              {renderLanguageSelectionMenu()}
            </MDBox>
          </MDBox>
        )}
      </Toolbar>
    </AppBar>
  );
}

// Setting default values for the props of DashboardNavbar
DashboardNavbar.defaultProps = {
  absolute: false,
  light: false,
  isMini: false,
};

// Typechecking props for the DashboardNavbar
DashboardNavbar.propTypes = {
  absolute: PropTypes.bool,
  light: PropTypes.bool,
  isMini: PropTypes.bool,
};

export default DashboardNavbar;
