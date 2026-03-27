import { createStore, combineReducers, applyMiddleware } from 'redux';
import thunk from 'redux-thunk';
import authReducer from './redux/reducers/authReducer';
import chatReducer from './redux/reducers/chatReducer';
import locationReducer from './redux/reducers/locationReducer';

const rootReducer = combineReducers({
  auth: authReducer,
  chat: chatReducer,
  location: locationReducer,
});

const store = createStore(rootReducer, applyMiddleware(thunk));

export default store;