/* eslint-disable */
import React from 'react';
import {Route, Switch } from 'react-router-dom';

// unauthenticated routes and layout
import Layout from './containers/layout';
import PublicHome from './containers/publicHome';
import Help from './containers/help';
import GoogleLogin from './containers/googleLogin';
import PublicLayout from './containers/layout/publicLayout';
import NewGeneNameReservation from './containers/reserve/new';
// authenticated curate inputs
import { requireAuthentication } from './containers/authenticateComponent';
// import CurateLayout from './containers/curateHome/layout';
import CurateHome from './containers/curateHome';
import Search from './containers/search';
import LocusLayout from './containers/locus/layout';
import LocusBasic from './containers/locus/basic';
// import LocusName from './containers/locus/name';
import LocusSummaries from './containers/locus/summaries';
import TriageIndex from './containers/triage';
import SpreadsheetUpload from './containers/spreadsheetUpload/index';
import Settings from './containers/settings/index';
import NotFound from './containers/curateHome/notFound';
import NewsLetter from './containers/newsLetter/index';
import PostTranslationModification from './containers/postTraslationModificaition/index';
// curate lit biz
import Blank from './components/blank';
import NewReference from './containers/newReference';
import CurateLit from './containers/curateLit/layout';
import CurateLitBasic from './containers/curateLit/basic';
import CurateLitPhenotype from './containers/curateLit/phenotype';
import GeneNameReservationIndex from './containers/reserve/index';
import GeneNameReservation from './containers/reserve/show';
import GeneNameReservationEdit from './containers/reserve/edit';
import GeneNameReservationStandardize from './containers/reserve/standardize';
import ColleaguesIndex from './containers/colleagues/index';
import ColleaguesShow from './containers/colleagues/show';
import NewColleague from './containers/colleagues/new';
import Regulation from './containers/regulation/index';
import Disease from './containers/disease/index';
import Complement from './containers/complement/index';
import FileCurate from './containers/fileCurate';
import FileCurateUpdate from './containers/fileCurate/updateFile.js';
import NewPhenotype from './containers/phenotype/new';
import SearchPhenotype from './containers/phenotype/search';
import EditPhenotype from './containers/phenotype/edit';
import NewAllele from './containers/allele/new';
import EditAllele from './containers/allele/edit';
import SearchAllele from './containers/allele/search';
import SubmitData from './containers/authorResponse/index';
import AuthorResponseShow from './containers/authorResponse/show';
import AuthorResponseProcess from './containers/authorResponse/process';
import LitGuide from './containers/litguide/search';
import AddLitGuide from './containers/litguide/add';
import EditLitGuide from './containers/litguide/edit';
import SearchFileMetadata from './containers/fileMetadata/search';
import EditFileMetadata from './containers/fileMetadata/edit';
import UploadSupplFiles from './containers/supplFiles/upload';
import LoadDataset from './containers/dataset/load';
import EditDataset from './containers/dataset/edit';
import EditDatasetSample from './containers/dataset/editSample';
import EditDatasetTrack from './containers/dataset/editTrack';
import SearchDataset from './containers/dataset/search';

//TODO: Fix the Routes.
export default (
  <div>
    <Switch>
      <Route render={(props) => <PublicLayout {...props}><NewColleague/></PublicLayout>} path='/new_colleague' />
      <Route render={(props) => <PublicLayout {...props}><NewGeneNameReservation /></PublicLayout>} path='/new_reservation' />
      <Route render={(props) => <PublicLayout {...props}><SubmitData /></PublicLayout>} path='/submit_data' />
      <Route render={() => <Layout>
        <Switch>
          <Route component={requireAuthentication(TriageIndex)} path='/triage' />
          <Route component={requireAuthentication(ColleaguesIndex)} path='/colleagues/triage' exact />
          <Route component={requireAuthentication(ColleaguesShow)} path='/colleagues/triage/:id' />
          <Route component={requireAuthentication(SpreadsheetUpload)} path='/spreadsheet_upload' />
          <Route component={requireAuthentication(Settings)} path='/settings' />
          <Route component={requireAuthentication(NewsLetter)} path='/newsletter' />
          <Route component={requireAuthentication(PostTranslationModification)} path='/ptm' />
          <Route component={Help} path='/help' />
          <Route component={requireAuthentication(Search)} path='/search' />
          <Route component={PublicHome} path='/login' />
          <Route component={GoogleLogin} path='/google_login' />
          <Route component={requireAuthentication(NewReference)} path='/curate/reference/new' />
          <Route component={requireAuthentication(CurateLit)} path='/curate/reference/:id' />
          <Route component={requireAuthentication(Regulation)} path='/regulation' />
          <Route component={requireAuthentication(Disease)} path='/disease' />
          <Route component={requireAuthentication(Complement)} path='/complement' />
	  <Route component={requireAuthentication(NewPhenotype)} path='/new_phenotype' />
	  <Route component={requireAuthentication(SearchPhenotype)} path='/search_phenotype' />  
          <Route component={requireAuthentication(EditPhenotype)} path='/edit_phenotype/:id' />
          <Route component={requireAuthentication(NewAllele)} path='/new_allele' />
          <Route component={requireAuthentication(EditAllele)} path='/curate/allele/:id' />
          <Route component={requireAuthentication(SearchAllele)} path='/search_allele' />
          <Route component={requireAuthentication(SearchFileMetadata)} path='/search_file_metadata' />
          <Route component={requireAuthentication(EditFileMetadata)} path='/edit_file_metadata/:id' />
          <Route component={requireAuthentication(UploadSupplFiles)} path='/upload_suppl_files' />
          <Route component={requireAuthentication(LoadDataset)} path='/load_dataset' />
          <Route component={requireAuthentication(EditDataset)} path='/curate/dataset/:id' />
          <Route component={requireAuthentication(EditDatasetSample)} path='/curate/datasetsample/:id' />
          <Route component={requireAuthentication(EditDatasetTrack)} path='/curate/datasettrack/:id' />
          <Route component={requireAuthentication(SearchDataset)} path='/search_dataset' />	     
          <Route component={requireAuthentication(LitGuide)} path='/litguide_todo' />
          <Route component={requireAuthentication(AddLitGuide)} path='/add_litguide' />
          <Route component={requireAuthentication(EditLitGuide)} path='/edit_litguide' />
          <Route component={requireAuthentication(LocusLayout)} path='/curate/locus/:id' />
          <Route component={requireAuthentication(FileCurate)} path='/file_curate' />
          <Route component={requireAuthentication(FileCurateUpdate)} path='/file_curate_update' />
          <Route component={requireAuthentication(GeneNameReservationIndex)} path='/reservations' exact />
          <Route component={requireAuthentication(GeneNameReservation)} path='/reservations/:id' exact />
          <Route component={requireAuthentication(GeneNameReservationEdit)} path='/reservations/:id/edit' exact />
          <Route component={requireAuthentication(GeneNameReservationStandardize)} path='/reservations/:id/standardize' exact />
          <Route component={requireAuthentication(AuthorResponseShow)} path='/author_responses' exact />
          <Route component={requireAuthentication(AuthorResponseProcess)} path='/author_responses/:id' exact/>
          <Route component={requireAuthentication(CurateHome)} path='/' exact/>
          <Route component={NotFound} path='*' />
        </Switch>

      </Layout>} path='/'/>
    </Switch>
  </div>
);

//TODO:  Keeping old routing for 
// export default (
//   <Route>
//     <Route component={Layout} path='/'>
//       <IndexRoute component={requireAuthentication(CurateHome)} />
//       <Route component={requireAuthentication(TriageIndex)} path='triage' />
//       <Route component={requireAuthentication(GeneNameReservationIndex)} path='reservations' />
//       <Route component={requireAuthentication(GeneNameReservation)} path='reservations/:id' />
//       <Route component={requireAuthentication(GeneNameReservationEdit)} path='reservations/:id/edit' />
//       <Route component={requireAuthentication(GeneNameReservationStandardize)} path='reservations/:id/standardize' />
//       <Route component={requireAuthentication(ColleaguesIndex)} path='colleagues/triage' />
//       <Route component={requireAuthentication(ColleaguesShow)} path='colleagues/triage/:id' />
//       <Route component={requireAuthentication(SpreadsheetUpload)} path='spreadsheet_upload' />
//       <Route component={requireAuthentication(Settings)} path='settings' />
//       <Route component={requireAuthentication(NewsLetter)} path='newsletter' />
//       <Route component={requireAuthentication(PostTranslationModification)} path='ptm' />
//       <Route component={Help} path='help' />
//       <Route component={requireAuthentication(Search)} path='search' />
//       <Route component={PublicHome} path='login' />
//       <Route component={GoogleLogin} path='google_login' />
//       <Route component={requireAuthentication(LocusLayout)} path='curate/locus/:id'>
//         {/* <IndexRoute component={requireAuthentication(LocusSummaries)} /> */}
//         <IndexRoute component={requireAuthentication(LocusBasic)} />
//         <Route component={requireAuthentication(LocusBasic)} path='basic' />
//         <Route component={requireAuthentication(LocusSummaries)} path='summaries' />
//         { /*<Route component={requireAuthentication(LocusName)} path='gene_name' /> */ }
//       </Route>
//       <Route component={requireAuthentication(NewReference)} path='curate/reference/new' />
//       <Route component={requireAuthentication(CurateLit)} path='curate/reference/:id'>
//         <IndexRoute component={requireAuthentication(CurateLitBasic)} />
//         <Route component={requireAuthentication(Blank)} path='protein' />
//         <Route component={requireAuthentication(CurateLitPhenotype)} path='phenotypes' />
//         <Route component={requireAuthentication(Blank)} path='go' />
//         <Route component={requireAuthentication(Blank)} path='datasets' />
//         <Route component={requireAuthentication(Blank)} path='regulation' />
//         <Route component={requireAuthentication(Blank)} path='interaction' />
//       </Route>
//       <Route component={requireAuthentication(Regulation)} path='regulation' />
//     </Route>
//     <Route component={PublicLayout}>
//       {/*<Route component={AuthorResponse} path='author_response' />*/}
//       <Route component={NewColleague} path='new_colleague' />
//       <Route component={NewGeneNameReservation} path='new_reservation' />
//     </Route>
//     <Route component={NotFound} path='*' />
//   </Route>
// );
