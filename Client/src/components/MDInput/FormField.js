// Material Dashboard 2 React components
import MDInput from "components/MDInput";

export default ({ label, ...rest }) => {
  return (
    <MDInput
      variant="standard"
      label={label}
      fullWidth
      {...rest}
    />
  );
}
