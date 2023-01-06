
import { useEffect, useState } from "react";

// react-router-dom components
import { useLocation, NavLink } from "react-router-dom";

// prop-types is a library for typechecking of props.
import PropTypes from "prop-types";

// @mui material components
import List from "@mui/material/List";
import Divider from "@mui/material/Divider";
import Link from "@mui/material/Link";
import Icon from "@mui/material/Icon";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import SidenavCollapse from "components/SideMenu/SidenavCollapse";

// Custom styles for the Sidenav
import SidenavRoot from "components/SideMenu/SidenavRoot";
import sidenavLogoLabel from "components/SideMenu/styles/sidenav";

import {
  usePlatformContext,
  setContextState,
} from "context";

import { dictionary } from "assets/translation";

const SideMenu = ({ color, brand, brandName, routes, ...rest }) => {
  const [openCollapse, setOpenCollapse] = useState(false);
  const [openNestedCollapse, setOpenNestedCollapse] = useState(false);
  const [controller, dispatch] = usePlatformContext();
  const { miniSidenav, transparentSidenav, hideSidenav, showSidenav, whiteSidenav, language, darkMode, user } = controller;

  const location = useLocation();
  const { pathname } = location;
  const collapseName = pathname.split("/").slice(1)[0];
  const items = pathname.split("/").slice(1);
  const itemParentName = items[1];
  const itemName = items[items.length - 1];

  let textColor = "white";

  if (transparentSidenav || (whiteSidenav && !darkMode)) {
    textColor = "dark";
  } else if (whiteSidenav && darkMode) {
    textColor = "inherit";
  }

  const closeSidenav = () => setContextState(dispatch, "hideSidenav", true);

  useEffect(() => {
    // A function that sets the mini state of the sidenav.
    function handleMiniSidenav() {
      setContextState(dispatch, "hideSidenav", window.innerWidth < 1200);
      setContextState(dispatch, "transparentSidenav", window.innerWidth < 1200 ? false : transparentSidenav);
      setContextState(dispatch, "whiteSidenav", window.innerWidth < 1200 ? false : whiteSidenav);
      setContextState(dispatch, "showSidenav", window.innerWidth < 1200);
    }

    setOpenCollapse(collapseName);

    /** 
     The event listener that's calling the handleMiniSidenav function when resizing the window.
    */
    window.addEventListener("resize", handleMiniSidenav);

    // Call the handleMiniSidenav function to set the state with the initial value.
    handleMiniSidenav();

    // Remove event listener on cleanup
    return () => window.removeEventListener("resize", handleMiniSidenav);
  }, [dispatch, location]);

  const renderCollapse = (collapses) => {
    return collapses.map(({ name, collapse, route, href, key, icon }) => {
      let returnValue;

      var nameString = "";
      if (Object.keys(dictionary.Routes).includes(name)) {
        nameString = dictionary.Routes[name][language];
      } else {
        nameString = name;
      }

      returnValue = href ? (
        <NavLink to={route} key={key}>
          <SidenavCollapse
            name={nameString}
            icon={icon}
            active={key === itemName}
          >
          </SidenavCollapse>
        </NavLink>
      ) : (
        <NavLink to={route} key={key} sx={{ textDecoration: "none" }}>
          <SidenavCollapse
            name={nameString}
            icon={icon}
            active={key === itemName}
          >
          </SidenavCollapse>
        </NavLink>
      );

      return <List key={key} sx={{paddingLeft: 2}}>
        {returnValue}
      </List>;
    });

  };

  // Render all the routes from the routes.js (All the visible items on the Sidenav)
  const renderRoutes = routes.map(({ type, name, icon, title, collapse, noCollapse, key, href, route, identified, deidentified }) => {
    let returnValue;

    if (type === "collapse") {
      if (!user.Clinician) {
        if (!deidentified) return returnValue;
      } else {
        if (!identified) return returnValue;
      }
    }

    var nameString = "";
    if (Object.keys(dictionary.Routes).includes(name)) {
      nameString = dictionary.Routes[name][language];
    } else {
      nameString = name;
    }

    if (type === "collapse") {
      if (noCollapse && route) {
        returnValue = (
          <NavLink to={route} key={key}>
            <SidenavCollapse
              name={nameString}
              icon={icon}
              active={key === itemName}
            >
              {collapse ? renderCollapse(collapse) : null}
            </SidenavCollapse>
          </NavLink>
        );
      } else {
        returnValue = (
          <SidenavCollapse
            key={key}
            name={nameString}
            icon={icon}
            active={key === collapseName}
            open={openCollapse === key}
            onClick={() => (openCollapse === key ? setOpenCollapse(false) : setOpenCollapse(key))}
          >
            {collapse ? renderCollapse(collapse) : null}
          </SidenavCollapse>
        );
      }
    } else if (type === "title") {
      returnValue = (
        <MDTypography
          key={key}
          color={textColor}
          display="block"
          variant="caption"
          fontWeight="bold"
          textTransform="uppercase"
          pl={3}
          mt={2}
          mb={1}
          ml={1}
        >
          {nameString}
        </MDTypography>
      );
    } else if (type === "divider") {
      returnValue = (
        <Divider
          key={key}
          light={
            (!darkMode && !whiteSidenav && !transparentSidenav) ||
            (darkMode && !transparentSidenav && whiteSidenav)
          }
        />
      );
    }

    return returnValue;
  });

  return (
    <SidenavRoot
      {...rest}
      variant="permanent"
      ownerState={{ transparentSidenav, whiteSidenav, miniSidenav, hideSidenav, showSidenav, darkMode }}
    >
      <MDBox pt={3} pb={1} px={4} textAlign="center">
        <MDBox
          display={{ xs: "block", xl: "none" }}
          position="absolute"
          top={0}
          right={0}
          p={1.625}
          onClick={closeSidenav}
          sx={{ cursor: "pointer" }}
        >
          <MDTypography variant="h6" color="secondary">
            <Icon sx={{ fontWeight: "bold" }}>close</Icon>
          </MDTypography>
        </MDBox>
        <MDBox component={NavLink} to="/" display="flex" alignItems="center">
          {brand && <MDBox component="img" src={brand} alt="Brand" width="2rem" />}
          <MDBox
            width={!brandName && "100%"}
            sx={(theme) => sidenavLogoLabel(theme, { miniSidenav })}
          >
            <MDTypography component="h6" variant="button" fontWeight="medium" color={textColor}>
              {brandName}
            </MDTypography>
          </MDBox>
        </MDBox>
      </MDBox>
      <Divider
        light={
          (!darkMode && !whiteSidenav && !transparentSidenav) ||
          (darkMode && !transparentSidenav && whiteSidenav)
        }
      />
      <List>{renderRoutes}</List>
    </SidenavRoot>
  );
}

export default SideMenu;