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

// Material Dashboard 2 PRO React TS components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";

// Material Dashboard 2 PRO React TS examples components
import DefaultNavbarDropdown from "components/Navbars/DefaultNavbar/DefaultNavbarDropdown";
import DefaultNavbarMobile from "components/Navbars/DefaultNavbar/DefaultNavbarMobile";

// Material Dashboard 2 PRO React TS Base Styles
import breakpoints from "assets/theme/base/breakpoints";

// BRAVO Context
import { usePlatformContext, setContextState } from "context";
import { dictionary } from "assets/translation.js";

function DefaultNavbar({ routes, brand, transparent, light }) {
  const [controller, dispatch] = usePlatformContext();
  const { user, language, darkMode } = controller;

  const navigate = useNavigate();

  const [customDropdown, setCustomDropdown] = useState({name: "", target: null, element: null});
  const [arrowRef, setArrowRef] = useState(null);
  const [mobileNavbar, setMobileNavbar] = useState(false);
  const [mobileView, setMobileView] = useState(false);

  const openMobileNavbar = () => setMobileNavbar(!mobileNavbar);

  const setLanguage = (lang) => {
    if (lang === "English") {
      setContextState(dispatch, "language", "en");
    } else if (lang === "中文") {
      setContextState(dispatch, "language", "zh");
    }
    setCustomDropdown({name: "", target: null, element: null});
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

  const redirectDashboard = () => {
    navigate("/dashboard", {replace: true});
  };

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
        <MDBox display="flex" justifyContent="space-between" alignItems="center">
          <MDBox
            component={Link}
            to="/"
            py={transparent ? 1.5 : 0.75}
            lineHeight={1}
            pl={{ xs: 0, lg: 1 }}
          >
            <MDTypography variant="button" fontWeight="bold" color={light ? "white" : "dark"}>
              {brand}
            </MDTypography>
          </MDBox>
          <MDBox display={{ xs: "none", lg: "flex" }}>
            <DefaultNavbarDropdown
              key={"languageOptions"}
              name={dictionary.SimplifiedNavbar.ChangeLanguage[language]}
              collapse={true}
              onMouseEnter={({ currentTarget }) => {
                setCustomDropdown({target: currentTarget, element: currentTarget, name: "languageOptions"});
              }}
              onMouseLeave={() => setCustomDropdown({...customDropdown, target: null})}
              light={light}
            />
            {Object.keys(user).length == 0 ? <DefaultNavbarDropdown
              key={"authOptions"}
              name={dictionary.SimplifiedNavbar.LoginRegister[language]}
              collapse={true}
              onMouseEnter={({ currentTarget }) => {
                setCustomDropdown({target: currentTarget, element: currentTarget, name: "authOptions"});
              }}
              onMouseLeave={() => setCustomDropdown({...customDropdown, target: null})}
              light={light}
            /> : <DefaultNavbarDropdown
              key={"dashboard"}
              name={dictionary.SimplifiedNavbar.Dashboard[language]}
              collapse={false}
              onClick={() => redirectDashboard()}
              light={light}
            />}
            <Popper
              anchorEl={customDropdown.target}
              popperRef={null}
              open={Boolean(customDropdown.target)}
              placement="top-start"
              transition
              style={{ zIndex: 999 }}
              modifiers={[
                {
                  name: "arrow",
                  enabled: true,
                  options: {
                    element: arrowRef,
                  },
                },
              ]}
              onMouseEnter={() => setCustomDropdown({...customDropdown, target: customDropdown.element})}
              onMouseLeave={() => {
                setCustomDropdown({...customDropdown, target: null, element: null, name: ""});
              }}
            >
              {({ TransitionProps }) => (
                <Grow
                  {...TransitionProps}
                  sx={{
                    transformOrigin: "left top",
                    background: ({ palette: { white } }) => white.main,
                  }}
                >
                  <MDBox borderRadius="lg">
                    <MDTypography variant="h1" color="white">
                      <Icon ref={setArrowRef} sx={{ mt: -3 }}>
                        arrow_drop_up
                      </Icon>
                    </MDTypography>
                    {customDropdown.name == "languageOptions" ? (
                    <MDBox shadow="lg" borderRadius="lg" p={1.625} mt={1}>
                      {["English", "中文"].map((lang) => {
                        return <MDTypography
                          key={lang}
                          display="flex"
                          justifyContent="space-between"
                          alignItems="center"
                          variant="button"
                          textTransform="capitalize"
                          minWidth={"12rem"}
                          color={"text"}
                          fontWeight={"regular"}
                          py={0.625}
                          px={2}
                          onClick={() => setLanguage(lang)}
                          sx={({ palette: { grey, dark }, borders: { borderRadius } }) => ({
                            borderRadius: borderRadius.md,
                            cursor: "pointer",
                            transition: "all 300ms linear",
                            "&:hover": {
                              backgroundColor: grey[200],
                              color: dark.main,

                              "& *": {
                                color: dark.main,
                              },
                            },
                          })}
                        >
                          <MDBox display="flex" alignItems="center" color="text">
                            <Icon sx={{ mr: 1 }}><ChangeCircleIcon/></Icon>
                            {lang}
                          </MDBox>
                        </MDTypography>
                      })}
                    </MDBox>
                    ) : null}
                    {customDropdown.name == "authOptions" ? (
                    <MDBox shadow="lg" borderRadius="lg" p={1.625} mt={1}>
                      {["Login", "Register"].map((type) => {
                        return <MDTypography
                          key={type}
                          component={Link} to={"/"+type.toLowerCase()}
                          display="flex"
                          justifyContent="space-between"
                          alignItems="center"
                          variant="button"
                          textTransform="capitalize"
                          minWidth={"12rem"}
                          color={"text"}
                          fontWeight={"regular"}
                          py={0.625}
                          px={2}
                          sx={({ palette: { grey, dark }, borders: { borderRadius } }) => ({
                            borderRadius: borderRadius.md,
                            cursor: "pointer",
                            transition: "all 300ms linear",
                            "&:hover": {
                              backgroundColor: grey[200],
                              color: dark.main,
                              "& *": {
                                color: dark.main,
                              },
                            },
                          })}
                        >
                          <MDBox display="flex" alignItems="center" color="text">
                            <Icon sx={{ mr: 1 }}> {type === "Login" ? <LoginIcon/> : <GroupAddIcon/>} </Icon>
                            {dictionary.SimplifiedNavbar[type][language]}
                          </MDBox>
                        </MDTypography>
                      })}
                    </MDBox>
                    ) : null}
                  </MDBox>
                </Grow>
              )}
            </Popper>

            <MDButton
              name={"Documentation"}
              size="small"
              href={"https://bravo-documentation.jcagle.solutions"}
              onClick={(event) => {
                event.currentTarget.blur();
              }}
              target={"_blank"}
              sx={{
                backgroundColor: "#11111177",
                color: "white !important",
                border: "1px solid",
                borderRadius: 0, 

                "&:hover": {
                  backgroundColor: "#11111177",
                  color: "white !important",
                },
              }}
            >
              {dictionary.SimplifiedNavbar.Documentation[language]}
            </MDButton>
          </MDBox>
          <MDBox
            display={{ xs: "inline-block", lg: "none" }}
            lineHeight={0}
            py={1.5}
            pl={1.5}
            color={transparent ? "white" : "inherit"}
            sx={{ cursor: "pointer" }}
            onClick={openMobileNavbar}
          >
            <Icon fontSize="default">{mobileNavbar ? "close" : "menu"}</Icon>
          </MDBox>
        </MDBox>
        <MDBox
          bgColor={transparent ? "white" : "transparent"}
          shadow={transparent ? "lg" : "none"}
          borderRadius="md"
          px={transparent ? 2 : 0}
        >
          {mobileView && <DefaultNavbarMobile routes={routes} open={mobileNavbar} onClick={() => setMobileNavbar(false)}/>}
        </MDBox>
      </MDBox>
    </Container>
  );
}

// Declaring default props for DefaultNavbar
DefaultNavbar.defaultProps = {
  brand: "UF BRAVO Platform",
  transparent: false,
  light: false,
  action: false,
};

// Typechecking props for the DefaultNavbar
DefaultNavbar.propTypes = {
  brand: PropTypes.string,
  routes: PropTypes.arrayOf(PropTypes.object).isRequired,
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
