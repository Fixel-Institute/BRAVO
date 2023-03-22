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
import { useLocation, Link, useNavigate } from "react-router-dom";
import PropTypes from "prop-types";

// @material-ui core components
import { 
  AppBar,
  Avatar,
  Dialog,
  Toolbar,
  Icon,
  IconButton,
  Menu,
  MenuItem,
  CircularProgress
} from "@mui/material";

import {
  Translate,
  ChangeCircle,
  PublishedWithChanges
} from '@mui/icons-material';

import MDBox from "components/MDBox";
import MDInput from "components/MDInput";
import MDBadge from "components/MDBadge";
import Breadcrumbs from "components/Breadcrumbs";
import ProcessingQueue from "components/ProcessingQueue";

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
import MDTypography from "components/MDTypography";

function DashboardNavbar({ absolute, light, isMini, fixedNavbar }) {
  const navigate = useNavigate();
  const [alert, setAlert] = useState(null);
  const [queueState, setQueueState] = useState({queues: [], show: false})
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
    SessionController.query("/api/queryProcessingQueue").then((response) => {
      setQueueState({...queueState, queues: response.data, show: false});
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });

    let client = new WebSocket(SessionController.getServer().replace("http","ws") + "/socket/notification");
    client.onerror = function() {
      console.log('Connection Error');
    };
    client.onopen = () => {
      client.send(JSON.stringify({
        "Authorization": SessionController.getRefreshToken()
      }));
    };
    client.onclose = () => {
      console.log('Connection Closed');
    };

    client.onmessage = (event) => {
      let content = JSON.parse(event.data);
      if (content["Notification"] === "QueueUpdate") {
        if (content["UpdateType"] === "JobCompletion") {
          setQueueState(currentState => {
            for (let i in currentState.queues) {
              if (currentState.queues[i].taskId == content["TaskID"]) {
                currentState.queues[i].state = content["State"];
              }
            }
            return {...currentState};
          });
        } else if (content["UpdateType"] === "NewJob") {
          setQueueState(currentState => {
            currentState.queues.push(content["NewJob"]);
            return {...currentState};
          });
        }
      }
    };

    return () => {
      client.close();
    }
  }, []);

  useEffect(() => {
    // Setting the navbar type
    if (fixedNavbar) {
      setNavbarType("sticky");
    } else {
      setNavbarType("static");
    }
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
      navigate("/", {replace: false});
    }).catch((error) => {
      if (error.response.status == 401) {
        SessionController.nullifyUser();
        setContextState(dispatch, "user", {});
        setContextState(dispatch, "patientID", null);
        navigate("/", {replace: false});
      } else {
        console.log(error)
      }
    });
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
      <MenuItem onClick={() => logoutUser()}>
        <i className="fa-solid fa-arrow-right-from-bracket" style={{paddingRight: 15}}></i>
        <MDTypography variant="button" fontWeight="regular" color="text">
          {dictionary.SimplifiedNavbar.Logout[language]}
        </MDTypography>
      </MenuItem>
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
        <MenuItem key={lang} onClick={() => setLanguage(lang)}>
          <Icon sx={{ mr: 1 }}><ChangeCircle/></Icon>
          <MDTypography variant="button" fontWeight="regular" color="text">
            {lang}
          </MDTypography>
        </MenuItem>
      ))}
    </Menu>
  );

  const getProcessingQueue = () => {
    SessionController.query("/api/queryProcessingQueue").then((response) => {
      setQueueState({...queueState, queues: response.data, show: true});
    }).catch((error) => {
      SessionController.displayError(error, setAlert);
    });
  };

  const clearQueue = (type) => {
    if (type == "All") {
      SessionController.query("/api/queryProcessingQueue", {
        clearQueue: "All",
      }).then((response) => {
        if (response.status == 200) {
          setQueueState({...queueState, queues:[], show: false});
        }
      }).catch((error) => {
        SessionController.displayError(error,setAlert);
      })
    } else if (type == "Complete") {
      SessionController.query("/api/queryProcessingQueue", {
        clearQueue: "Complete",
      }).then((response) => {
        if (response.status == 200) {
          setQueueState(currentState => {
            currentState.queues = currentState.queues.filter((item) => item.state != "Complete");
            return {...currentState};
          });
        }
      }).catch((error) => {
        SessionController.displayError(error,setAlert);
      })
    }
  };

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
      {alert}
      <Toolbar sx={(theme) => navbarContainer(theme)}>
        <MDBox color="inherit" mb={{ xs: 1, md: 0 }} sx={(theme) => navbarRow(theme, { isMini })}>
          <Breadcrumbs icon="home" title={route[route.length - 1]} route={route} light={light} />
          <IconButton sx={{display: {xs: "none", xl: "block"}}} onClick={handleMiniSidenav} size="small" disableRipple>
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
            <MDBox pr={1}/>
            <MDBox color={light ? "white" : "inherit"}>
              <IconButton
                size="small"
                disableRipple
                color="inherit"
                sx={navbarIconButton}
                variant="contained"
                onClick={(event) => getProcessingQueue()}
              >
                {queueState.queues.filter((item) => item.state === "InProgress").length > 0 ? <CircularProgress color={"info"} fontSize="large" /> : <PublishedWithChanges color={"info"} fontSize="large" />}
              </IconButton>
              <IconButton
                size="small"
                disableRipple
                color="inherit"
                sx={navbarIconButton}
                aria-haspopup="true"
                variant="contained"
                onClick={(event) => handleOpenMenu(event, "LanguageMenu")}
              >
                <Translate fontSize="large" />
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
                <MDBadge badgeContent={null} color="error" size="xs" circular>
                  <Avatar src={""} />
                </MDBadge>
              </IconButton>
              {renderProfileMenu()}
              {renderLanguageSelectionMenu()}
            </MDBox>
          </MDBox>
        )}
      </Toolbar>
      
      <Dialog
        open={queueState.show}
        PaperProps={{
          sx: {
            minWidth: 700
          }
        }}
        onClose={() => setQueueState({...queueState, show: false})}
      >
        <ProcessingQueue queues={queueState.queues} clearQueue={clearQueue}/>
      </Dialog>
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
