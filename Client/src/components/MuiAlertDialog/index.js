import PropTypes from "prop-types";

import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
} from "@mui/material";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";

export default function MuiAlertDialog({title, message, denyButton, cancelButton, handleClose, confirmText, handleConfirm, cancelText, handleCancel, denyText, handleDeny}) {
  
  return (
    <Dialog
      open={true}
      onClose={handleClose}
      sx={{
        padding: 15
      }}
    >
      <DialogTitle>
        <MDTypography align="center" fontSize={30}>
          {title}
        </MDTypography>
      </DialogTitle>
      <DialogContent sx={{paddingLeft: 5, paddingRight: 5}}>
        <DialogContentText>
          <MDTypography variant="p" align="center" fontSize={20}>
            {message}
          </MDTypography>
        </DialogContentText>
      </DialogContent>
      <MDBox display={"flex"} justifyContent={"space-around"} sx={{paddingLeft: 5, paddingRight: 5, paddingTop: 2, paddingBottom: 2}}>
        {cancelButton ? (
        <MDButton variant="gradient" color="secondary" onClick={handleCancel} sx={{minWidth: 100}}>
          {cancelText}
        </MDButton>) : null}
        {denyButton ? (
        <MDButton variant="gradient" color="error" onClick={handleDeny} sx={{minWidth: 100}}>
          {denyText}
        </MDButton>) : null}
        <MDButton variant="gradient" color="info" onClick={handleConfirm} sx={{minWidth: 100}}>
          {confirmText}
        </MDButton>
      </MDBox>
    </Dialog>
  )
}

// Declaring default props for DefaultNavbar
MuiAlertDialog.defaultProps = {
  title: "Alert",
  message: "Unknown Error",
  open: true,
  cancelButton: false,
  denyButton: false,

  confirmText: "Confirm",
  cancelText: "Cancel",
  denyText: "No",
};

// Typechecking props for the DefaultNavbar
MuiAlertDialog.propTypes = {
  title: PropTypes.string,
  message: PropTypes.string,
  denyButton: PropTypes.bool,
  cancelButton: PropTypes.bool,

  confirmText: PropTypes.string,
  cancelText: PropTypes.string,
  denyText: PropTypes.string,
  handleClose: PropTypes.func.isRequired,
  handleConfirm: PropTypes.func.isRequired,
  handleCancel: PropTypes.func,
  handleDeny: PropTypes.func,
};
