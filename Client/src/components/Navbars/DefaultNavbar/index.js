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

import { useState, useEffect, Fragment } from "react";

// prop-types is a library for typechecking of props.
import PropTypes from "prop-types";

// react-router components
import { Link, useNavigate } from "react-router-dom";

// @mui material components
import { 
  Container, 
  Dialog,
  DialogActions,
  DialogContent,
  TextField,
  Icon, 
  Popper, 
  Grow, 
  Grid, 
  Divider,
  Menu,
  MenuItem,
} from "@mui/material";
import MuiLink from "@mui/material/Link";

import ChangeCircleIcon from '@mui/icons-material/ChangeCircle';
import LoginIcon from '@mui/icons-material/Login';
import GroupAddIcon from '@mui/icons-material/GroupAdd';
import StorageIcon from '@mui/icons-material/Storage';
import CheckIcon from '@mui/icons-material/Check';

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";

import DefaultNavbarLink from "./DefaultNavbarLink";
import DefaultNavbarMobile from "components/Navbars/DefaultNavbar/DefaultNavbarMobile";

import breakpoints from "assets/theme/base/breakpoints";

// BRAVO Context
import { usePlatformContext, setContextState } from "context";
import { dictionary } from "assets/translation.js";
import { SessionController } from 'database/session-control';

function DefaultNavbar({ transparent, light, action }) {
  const [ controller, dispatch ] = usePlatformContext();
  const { darkMode, language } = controller;

  const [mobileNavbar, setMobileNavbar] = useState(false);
  const [mobileView, setMobileView] = useState(false);
  const [openMenu, setOpenMenu] = useState(false);
  const [whichMenu, setWhichMenu] = useState("");
  const [currentHost, setCurrentHost] = useState("Localhost");
  const [customServer, setCustomServer] = useState({show: false, address: ""});

  const openMobileNavbar = ({ currentTarget }) => setMobileNavbar(currentTarget.parentNode);
  const closeMobileNavbar = () => setMobileNavbar(false);
  const handleOpenMenu = (event, name) => {
    setOpenMenu(event.currentTarget);
    setWhichMenu(name);
  }
  const handleCloseMenu = () => {
    setWhichMenu("");
    setOpenMenu(null);
  };

  const setLanguage = (lang) => {
    if (lang === "English") {
      setContextState(dispatch, "language", "en");
    } else if (lang === "中文") {
      setContextState(dispatch, "language", "zh");
    }
    handleCloseMenu();
  };

  const setServer = (server) => {
    handleCloseMenu();

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

  useEffect(() => {
    // A function that sets the display state for the DefaultNavbarMobile.
    function displayMobileNavbar() {
      if (window.innerWidth < breakpoints.values.lg) {
        setMobileView(true);
        setMobileNavbar(false);
      } else {
        setMobileView(false);
        setMobileNavbar(false);
      }
    }

    const serverAddress = SessionController.getServer();
    if (serverAddress == "http://localhost:3001") {
      setCurrentHost("Localhost");
    } else if (serverAddress == "https://bravo-server.jcagle.solutions") {
      setCurrentHost("DemoServer");
    } else {
      setCurrentHost("CustomizedServer");
    }
    /** 
     The event listener that's calling the displayMobileNavbar function when 
     resizing the window.
    */
    window.addEventListener("resize", displayMobileNavbar);

    // Call the displayMobileNavbar function to set the state with the initial value.
    displayMobileNavbar();

    // Remove event listener on cleanup
    return () => window.removeEventListener("resize", displayMobileNavbar);
  }, []);

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
        <MenuItem key={lang} onClick={() => setLanguage(lang)}>
          <Icon sx={{ mr: 1 }}><ChangeCircleIcon/></Icon>
          <MDTypography variant="button" fontWeight="regular" color="text">
            {lang}
          </MDTypography>
        </MenuItem>
      ))}
    </Menu>
  );

  // Render the notifications menu
  const renderServerSelectionMenu = () => (
    <Menu
      anchorEl={openMenu}
      anchorReference={null}
      anchorOrigin={{
        vertical: "bottom",
        horizontal: "left",
      }}
      open={whichMenu === "ServerMenu"}
      onClose={handleCloseMenu}
      sx={{ mt: 2 }}
    >
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
    </Menu>
  );

  return (
    <Container>
      <MDBox
        py={1}
        px={{ xs: 4, sm: transparent ? 2 : 3, lg: transparent ? 0 : 2 }}
        my={3}
        mx={3}
        width="calc(100% - 48px)"
        borderRadius="lg"
        shadow={transparent ? "none" : "md"}
        color={light ? "white" : "dark"}
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        position="absolute"
        left={0}
        zIndex={3}
        sx={({
          palette: { transparent: transparentColor, white, background },
          functions: { rgba },
        }) => ({
          backgroundColor: transparent
            ? transparentColor.main
            : rgba(darkMode ? background.sidenav : white.main, 0.8),
          backdropFilter: transparent ? "none" : `saturate(200%) blur(30px)`,
        })}
      >
        <MDBox
          component={Link}
          to="/"
          py={transparent ? 1.5 : 0.75}
          lineHeight={1}
          pl={{ xs: 0, lg: 1 }}
        >
          <MDTypography variant="button" fontWeight="bold" color={light ? "white" : "dark"}>
            {"UF BRAVO Platform"}
          </MDTypography>
        </MDBox>
        <MDBox color="inherit" display={{ xs: "none", lg: "flex" }} m={0} p={0}>
          <DefaultNavbarLink 
            icon={<StorageIcon/>}
            name={dictionary.SimplifiedNavbar.ChangeServer[language]}
            onClick={(event) => handleOpenMenu(event, "ServerMenu")} 
            light={light} 
          />
          <DefaultNavbarLink 
            icon={<ChangeCircleIcon/>}
            name={dictionary.SimplifiedNavbar.ChangeLanguage[language]}
            onClick={(event) => handleOpenMenu(event, "LanguageMenu")} 
            light={light} 
          />
          <DefaultNavbarLink
            icon={<LoginIcon/>}
            name={dictionary.SimplifiedNavbar.Login[language]}
            route="/login"
            light={light}
          />
          <DefaultNavbarLink
            icon={<GroupAddIcon/>}
            name={dictionary.SimplifiedNavbar.Register[language]}
            route="/register"
            light={light}
          />
          {renderLanguageSelectionMenu()}
          {renderServerSelectionMenu()}


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
        </MDBox>
        {action &&
          (action.type === "internal" ? (
            <MDBox display={{ xs: "none", lg: "inline-block" }}>
              <MDButton
                component={Link}
                to={action.route}
                variant="gradient"
                color={action.color ? action.color : "info"}
                size="small"
              >
                {action.label}
              </MDButton>
            </MDBox>
          ) : (
            <MDBox display={{ xs: "none", lg: "inline-block" }}>
              <MDButton
                component="a"
                href={action.route}
                target="_blank"
                rel="noreferrer"
                variant="gradient"
                color={action.color ? action.color : "info"}
                size="small"
                sx={{ mt: -0.3 }}
              >
                {action.label}
              </MDButton>
            </MDBox>
          ))}
        <MDBox
          display={{ xs: "inline-block", lg: "none" }}
          lineHeight={0}
          py={1.5}
          pl={1.5}
          color="inherit"
          sx={{ cursor: "pointer" }}
          onClick={openMobileNavbar}
        >
          <Icon fontSize="default">{mobileNavbar ? "close" : "menu"}</Icon>
        </MDBox>
      </MDBox>
      {mobileView && <DefaultNavbarMobile open={mobileNavbar} close={closeMobileNavbar} />}
    </Container>
  );
}

// Setting default values for the props of DefaultNavbar
DefaultNavbar.defaultProps = {
  transparent: false,
  light: false,
  action: false,
};

// Typechecking props for the DefaultNavbar
DefaultNavbar.propTypes = {
  transparent: PropTypes.bool,
  light: PropTypes.bool,
  action: PropTypes.oneOfType([
    PropTypes.bool,
    PropTypes.shape({
      type: PropTypes.oneOf(["external", "internal"]).isRequired,
      route: PropTypes.string.isRequired,
      color: PropTypes.oneOf([
        "primary",
        "secondary",
        "info",
        "success",
        "warning",
        "error",
        "dark",
        "light",
      ]),
      label: PropTypes.string.isRequired,
    }),
  ]),
};

export default DefaultNavbar;
