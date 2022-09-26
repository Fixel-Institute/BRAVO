import React from "react";

import {
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio
} from "@mui/material";

const RadioButtonGroup = ({defaultValue, options, row, onChange}) => {
  return (
    <RadioGroup
      value={defaultValue}
      row={row}
      onChange={onChange}
    >
      {options.map((option) => {
        return <FormControlLabel key={option.value} value={option.value} control={<Radio />} label={option.label} />
      })}
    </RadioGroup>
  );
};

export default RadioButtonGroup;