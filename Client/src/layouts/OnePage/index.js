import PropTypes from "prop-types";

// @mui material components
import Grid from "@mui/material/Grid";

import MDBox from "components/MDBox";

import DefaultNavbar from "components/Navbars/DefaultNavbar";
import PageLayout from "./PageLayout";

// Authentication pages components
import Footer from "components/Footers/OnePageFooter";

export default function OnePageLayout({ image, wide, children }) {
  return (
    <PageLayout>
      <DefaultNavbar
        routes={[]}
        transparent
        light
      />
      <MDBox
        position="absolute"
        width="100%"
        minHeight="100vh"
        sx={{
          backgroundImage: ({ functions: { linearGradient, rgba }, palette: { gradients } }) =>
            image &&
            `${linearGradient(
              rgba(gradients.dark.main, 0.6),
              rgba(gradients.dark.state, 0.6)
            )}, url(${image})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat",
        }}
      />
      <MDBox px={1} width="100%" height="100vh" mx="auto">
        <Grid container spacing={1} justifyContent="center" alignItems="center" height="100%">
          {!wide ? (
            <Grid item xs={11} md={8} lg={6} xl={3}>
              {children}
            </Grid>
            ) : (
            <Grid item xs={12} sm={11}>
              {children}
            </Grid>
          )}
        </Grid>
      </MDBox>
      <Footer light />
    </PageLayout>
  );
}

OnePageLayout.defaultProps = {
  wide: false
};

OnePageLayout.propTypes = {
  image: PropTypes.string.isRequired,
  wide: PropTypes.bool,
  children: PropTypes.node.isRequired,
};
