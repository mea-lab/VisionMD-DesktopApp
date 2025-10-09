import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';

const JSONUploadDialog = ({
  dialogOpen,
  setDialogOpen,
  uploadError,
  setUploadError,
}) => {

  const handleClose = () => {
    setDialogOpen(false);
    setUploadError(null);
  }

  return (
    <Dialog
      open={dialogOpen}
      onClose={handleClose}
      PaperProps={{
        sx: {
          backgroundColor: '#333338',
          borderRadius: 3,
          minWidth: 400,
        },
      }}
    >
      <DialogTitle className="text-gray-100">
        <div className="flex flex-row w-full justify-between items-center">
          Project Setup
          <IconButton onClick={handleClose}>
            <CloseIcon className="text-gray-100" />
          </IconButton>
        </div>
      </DialogTitle>

      <DialogContent>
        
          { uploadError ? (
            <div className='flex flex-col w-full h-full justify-center items-left gap-10 text-gray-100'>
              <Typography color="error" sx={{ mt: 2, mb: 2, textAlign: 'left', whiteSpace: 'pre-line' }}>
                {uploadError}
              </Typography>
            </div>
          ) : (
            <div className='flex flex-col w-full h-full justify-center items-center gap-5 text-gray-100'>
              <div>Video upload in progress</div>
              <CircularProgress className='my-4' size={80} />
            </div>
          )
        }
      </DialogContent>
    </Dialog>
  );
};

export default JSONUploadDialog;
